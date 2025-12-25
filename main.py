from datetime import datetime, timedelta, date as dt_date, time as dt_time
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Patient, Doctor, Appointment
import models

# --- Create DB tables ---
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital API", version="0.1.0")

# -------------------------
# Auth (simple demo auth)
# -------------------------
SECRET_KEY = "CHANGE_THIS_TO_SOMETHING_RANDOM_AND_LONG"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# demo user store
FAKE_USERS = {
    "admin": {"username": "admin", "password": "admin123"}
}


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# -------------------------
# DB dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Schemas
# -------------------------
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PatientCreate(BaseModel):
    name: str
    phone: str
    age: int = Field(ge=0)
    gender: str


class PatientOut(PatientCreate):
    id: int
    class Config:
        from_attributes = True


class DoctorCreate(BaseModel):
    name: str
    phone: str
    specialty: str


class DoctorOut(DoctorCreate):
    id: int
    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: dt_date
    time: dt_time


class AppointmentOut(AppointmentCreate):
    id: int
    token_number: int
    class Config:
        from_attributes = True


# -------------------------
# Auth endpoint
# -------------------------
@app.post("/token", response_model=TokenOut)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


# -------------------------
# Patients CRUD
# -------------------------
@app.post("/patients", response_model=PatientOut)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    p = Patient(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@app.get("/patients", response_model=List[PatientOut])
def list_patients(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return db.query(Patient).all()


@app.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return p


@app.put("/patients/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, payload: PatientCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    for k, v in payload.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(p)
    db.commit()
    return {"detail": "Patient deleted"}


# -------------------------
# Doctors CRUD
# -------------------------
@app.post("/doctors", response_model=DoctorOut)
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    d = Doctor(**payload.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@app.get("/doctors", response_model=List[DoctorOut])
def list_doctors(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return db.query(Doctor).all()


@app.get("/doctors/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return d


@app.put("/doctors/{doctor_id}", response_model=DoctorOut)
def update_doctor(doctor_id: int, payload: DoctorCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    for k, v in payload.model_dump().items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d


@app.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db.delete(d)
    db.commit()
    return {"detail": "Doctor deleted"}


# -------------------------
# Appointments CRUD
# -------------------------
@app.post("/appointments", response_model=AppointmentOut)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    # ensure patient/doctor exist
    if not db.query(Patient).filter(Patient.id == payload.patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    if not db.query(Doctor).filter(Doctor.id == payload.doctor_id).first():
        raise HTTPException(status_code=404, detail="Doctor not found")

    appt = Appointment(**payload.model_dump(), token_number=0)
    db.add(appt)
    db.commit()
    db.refresh(appt)

    # token_number = id (simple token system)
    appt.token_number = appt.id
    db.commit()
    db.refresh(appt)
    return appt


@app.get("/appointments", response_model=List[AppointmentOut])
def list_appointments(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return db.query(Appointment).all()


@app.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@app.put("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, payload: AppointmentCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if not db.query(Patient).filter(Patient.id == payload.patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    if not db.query(Doctor).filter(Doctor.id == payload.doctor_id).first():
        raise HTTPException(status_code=404, detail="Doctor not found")

    for k, v in payload.model_dump().items():
        setattr(appt, k, v)

    db.commit()
    db.refresh(appt)
    return appt


@app.delete("/appointments/{appointment_id}")
def delete_appointment(appointment_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    db.delete(appt)
    db.commit()
    return {"detail": "Appointment deleted"}
