
import os
from pathlib import Path
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error, IntegrityError
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Path as ApiPath
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ------------------------------------------------
# 1. Application Configuration
# ------------------------------------------------

load_dotenv()

app = FastAPI(title="Hospital Patient Management API")

BASE_DIR = Path(__file__).resolve().parent


# ------------------------------------------------
# 2. MySQL Database Connection
# ------------------------------------------------

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "hospital_db")
    )


@contextmanager
def database():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        yield connection, cursor

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except IntegrityError as e:
        if connection:
            connection.rollback()

        if e.errno == 1062:
            raise HTTPException(
                status_code=409,
                detail="Patient ID already exists"
            )

        raise HTTPException(
            status_code=400,
            detail="Database integrity constraint failed"
        )

    except Error as e:
        if connection:
            connection.rollback()

        print("Database Error:", e)

        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ------------------------------------------------
# 3. Pydantic Models
# ------------------------------------------------

class Patient(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        strict=True
    )

    patient_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=0, le=120)
    disease: str = Field(min_length=2, max_length=150)
    doctor_name: str = Field(min_length=2, max_length=100)

    @field_validator("name", "disease", "doctor_name")
    @classmethod
    def reject_blank(cls, value):
        if not value.strip():
            raise ValueError("Field cannot be blank")
        return value


class DiagnosisUpdate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    disease: str = Field(min_length=2, max_length=150)

    @field_validator("disease")
    @classmethod
    def reject_blank(cls, value):
        if not value.strip():
            raise ValueError("Disease cannot be blank")
        return value


class DoctorUpdate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    doctor_name: str = Field(min_length=2, max_length=100)

    @field_validator("doctor_name")
    @classmethod
    def reject_blank(cls, value):
        if not value.strip():
            raise ValueError("Doctor name cannot be blank")
        return value


# ------------------------------------------------
# 4. Home Page
# ------------------------------------------------

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


# ------------------------------------------------
# 5. Register Patient - POST
# ------------------------------------------------

@app.post("/patients", status_code=201)
def register_patient(patient: Patient):

    with database() as (connection, cursor):

        sql = """
            INSERT INTO patients
            (patient_id, name, age, disease,
             doctor_name, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            patient.patient_id,
            patient.name,
            patient.age,
            patient.disease,
            patient.doctor_name,
            "Admitted"
        )

        cursor.execute(sql, values)
        connection.commit()

    return {"message": "Patient registered successfully"}


# ------------------------------------------------
# 6. Display All Patients - GET
# ------------------------------------------------

@app.get("/patients")
def display_patients():

    with database() as (connection, cursor):

        cursor.execute(
            "SELECT * FROM patients ORDER BY patient_id"
        )

        return cursor.fetchall()


# ------------------------------------------------
# 7. Search Patient by ID - GET
# ------------------------------------------------

@app.get("/patients/{patient_id}")
def search_patient(
    patient_id: int = ApiPath(gt=0)
):

    with database() as (connection, cursor):

        cursor.execute(
            "SELECT * FROM patients WHERE patient_id = %s",
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        return patient


# ------------------------------------------------
# 8. Update Diagnosis - PUT
# ------------------------------------------------

@app.put("/patients/{patient_id}/diagnosis")
def update_diagnosis(
    data: DiagnosisUpdate,
    patient_id: int = ApiPath(gt=0)
):

    with database() as (connection, cursor):

        cursor.execute(
            "SELECT status FROM patients "
            "WHERE patient_id = %s FOR UPDATE",
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:
            raise HTTPException(404, "Patient not found")

        if patient["status"] == "Discharged":
            raise HTTPException(
                409,
                "Cannot update a discharged patient"
            )

        cursor.execute(
            "UPDATE patients SET disease = %s "
            "WHERE patient_id = %s",
            (data.disease, patient_id)
        )

        connection.commit()

    return {"message": "Diagnosis updated successfully"}


# ------------------------------------------------
# 9. Update Doctor - PUT
# ------------------------------------------------

@app.put("/patients/{patient_id}/doctor")
def update_doctor(
    data: DoctorUpdate,
    patient_id: int = ApiPath(gt=0)
):

    with database() as (connection, cursor):

        cursor.execute(
            "SELECT status FROM patients "
            "WHERE patient_id = %s FOR UPDATE",
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:
            raise HTTPException(404, "Patient not found")

        if patient["status"] == "Discharged":
            raise HTTPException(
                409,
                "Cannot update a discharged patient"
            )

        cursor.execute(
            "UPDATE patients SET doctor_name = %s "
            "WHERE patient_id = %s",
            (data.doctor_name, patient_id)
        )

        connection.commit()

    return {"message": "Doctor updated successfully"}


# ------------------------------------------------
# 10. Discharge Patient - PUT
# ------------------------------------------------

@app.put("/patients/{patient_id}/discharge")
def discharge_patient(
    patient_id: int = ApiPath(gt=0)
):

    with database() as (connection, cursor):

        cursor.execute(
            "SELECT status FROM patients "
            "WHERE patient_id = %s FOR UPDATE",
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:
            raise HTTPException(404, "Patient not found")

        if patient["status"] == "Discharged":
            raise HTTPException(
                409,
                "Patient is already discharged"
            )

        cursor.execute(
            "UPDATE patients SET status = %s "
            "WHERE patient_id = %s",
            ("Discharged", patient_id)
        )

        connection.commit()

    return {"message": "Patient discharged successfully"}


# ------------------------------------------------
# 11. Delete Patient by ID - DELETE
# ------------------------------------------------

@app.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: int = ApiPath(gt=0)
):

    with database() as (connection, cursor):

        cursor.execute(
            "DELETE FROM patients WHERE patient_id = %s",
            (patient_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Patient not found")

        connection.commit()

    return {"message": "Patient deleted successfully"}


# ------------------------------------------------
# 12. Delete All Patients - DELETE
# ------------------------------------------------

@app.delete("/patients")
def delete_all_patients():

    with database() as (connection, cursor):

        cursor.execute("DELETE FROM patients")
        deleted_count = cursor.rowcount

        connection.commit()

    return {
        "message": "All patients deleted successfully",
        "deleted_count": deleted_count
    }
