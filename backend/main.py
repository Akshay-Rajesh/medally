import random
import string
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "sqlite:///./med_tracker.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password = Column(String, nullable=True)
    role = Column(String, nullable=False) # 'caregiver' or 'patient'
    caregiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    access_code = Column(String, unique=True, nullable=True)

class Medication(Base):
    __tablename__ = "medications"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medicine_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    schedule_time = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Family Med Tracker MVP")

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

@app.post("/auth/register-caregiver")
def register_caregiver(user: RegisterCaregiver, db: Session = Depends(get_db)):
    db_user = User(name=user.name, email=user.email, password=user.password, role="caregiver")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "name": db_user.name, "role": db_user.role}

@app.post("/auth/login-caregiver")
def login_caregiver(creds: LoginCaregiver, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == creds.email, User.password == creds.password, User.role == "caregiver").first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"id": user.id, "name": user.name, "role": user.role}

@app.post("/patients/add")
def add_patient(data: AddPatient, db: Session = Depends(get_db)):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    db_patient = User(
        name=data.name,
        role="patient",
        caregiver_id=data.caregiver_id,
        access_code=code
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return {"id": db_patient.id, "name": db_patient.name, "access_code": db_patient.access_code}

@app.post("/auth/patient-code-login")
def patient_code_login(data: PatientCodeLogin, db: Session = Depends(get_db)):
    patient = db.query(User).filter(User.access_code == data.access_code.upper(), User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Invalid access code")
    return {"id": patient.id, "name": patient.name, "role": patient.role}

@app.get("/users/family/{caregiver_id}")
def get_family_members(caregiver_id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.caregiver_id == caregiver_id).all()

@app.post("/medications")
def add_medication(med: MedicationCreate, db: Session = Depends(get_db)):
    db_med = Medication(**med.dict())
    db.add(db_med)
    db.commit()
    return {"message": "Medication added"}

@app.get("/medications/{patient_id}")
def get_medications(patient_id: int, db: Session = Depends(get_db)):
    return db.query(Medication).filter(Medication.patient_id == patient_id, Medication.is_active == True).all()