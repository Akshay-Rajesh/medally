import random
import string
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

DATABASE_URL = "sqlite:///./med_tracker.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODELS ---

class Caregiver(Base):
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    
    patients = relationship("Patient", back_populates="caregiver", cascade="all, delete-orphan")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    name = Column(String, nullable=False)
    access_code = Column(String, unique=True, nullable=False)

    caregiver = relationship("Caregiver", back_populates="patients")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    logs = relationship("MedicationLog", back_populates="patient", cascade="all, delete-orphan")

class Medication(Base):
    __tablename__ = "medications"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medicine_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    schedule_time = Column(String, nullable=False) # e.g. "09:00"
    is_active = Column(Boolean, default=True)

    patient = relationship("Patient", back_populates="medications")
    logs = relationship("MedicationLog", back_populates="medication", cascade="all, delete-orphan")

class MedicationLog(Base):
    __tablename__ = "medication_logs"
    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    scheduled_time = Column(String, nullable=False)
    status = Column(String, default="PENDING") # 'PENDING', 'TAKEN', 'MISSED'
    confirmed_at = Column(DateTime, nullable=True)

    medication = relationship("Medication", back_populates="logs")
    patient = relationship("Patient", back_populates="logs")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Family Med Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PYDANTIC SCHEMAS ---

class RegisterCaregiver(BaseModel):
    name: str
    email: str
    password: str

class LoginCaregiver(BaseModel):
    email: str
    password: str

class AddPatient(BaseModel):
    name: str
    caregiver_id: int

class PatientCodeLogin(BaseModel):
    access_code: str

class MedicationCreate(BaseModel):
    patient_id: int
    medicine_name: str
    dosage: str
    schedule_time: str

class MedicationUpdate(BaseModel):
    medicine_name: str
    dosage: str
    schedule_time: str

# --- ENDPOINTS ---

@app.post("/auth/register-caregiver")
def register_caregiver(user: RegisterCaregiver, db: Session = Depends(get_db)):
    existing = db.query(Caregiver).filter(Caregiver.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = Caregiver(name=user.name, email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "name": db_user.name, "role": "caregiver"}

@app.post("/auth/login-caregiver")
def login_caregiver(creds: LoginCaregiver, db: Session = Depends(get_db)):
    user = db.query(Caregiver).filter(Caregiver.email == creds.email, Caregiver.password == creds.password).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"id": user.id, "name": user.name, "role": "caregiver"}

@app.post("/patients/add")
def add_patient(data: AddPatient, db: Session = Depends(get_db)):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    db_patient = Patient(
        name=data.name,
        caregiver_id=data.caregiver_id,
        access_code=code
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return {"id": db_patient.id, "name": db_patient.name, "access_code": db_patient.access_code}

@app.post("/auth/patient-code-login")
def patient_code_login(data: PatientCodeLogin, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.access_code == data.access_code.upper()).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Invalid access code")
    return {"id": patient.id, "name": patient.name, "role": "patient"}

@app.get("/users/family/{caregiver_id}")
def get_family_members(caregiver_id: int, db: Session = Depends(get_db)):
    patients = db.query(Patient).filter(Patient.caregiver_id == caregiver_id).all()
    return [{"id": p.id, "name": p.name, "access_code": p.access_code, "role": "patient"} for p in patients]

@app.post("/medications")
def add_medication(med: MedicationCreate, db: Session = Depends(get_db)):
    db_med = Medication(**med.dict())
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return {"message": "Medication added", "id": db_med.id}

@app.get("/medications/{patient_id}")
def get_medications(patient_id: int, db: Session = Depends(get_db)):
    return db.query(Medication).filter(Medication.patient_id == patient_id, Medication.is_active == True).all()

@app.put("/medications/{medication_id}")
def update_medication(medication_id: int, med_update: MedicationUpdate, db: Session = Depends(get_db)):
    med = db.query(Medication).filter(Medication.id == medication_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    med.medicine_name = med_update.medicine_name
    med.dosage = med_update.dosage
    med.schedule_time = med_update.schedule_time
    db.commit()
    return {"message": "Medication updated successfully"}

@app.delete("/medications/{medication_id}")
def delete_medication(medication_id: int, db: Session = Depends(get_db)):
    med = db.query(Medication).filter(Medication.id == medication_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    db.delete(med)
    db.commit()
    return {"message": "Medication deleted successfully"}