# TODO: Active Patients / Patient Management (Patientlist) table

## Step 1: Locate/implement `patientlist` model

- Search for legacy table `Patientlist` mapping (unmanaged model with `db_table='patientlist'`).
- Identify required fields: Registry DateTime, ID, Birthdate, Gender, and the patient name parts.

## Step 2: Add view/query

- Update `core/views.py` patients list route to query `patientlist` and return “active patients”.
- Build `patient_display_name` as: `LastName + FirstName Initials only`.

## Step 3: Update template

- Ensure `templates/patients_list.html` renders the row fields produced by the backend.

## Step 4: Testing

- Run the server and verify the Patients Management page renders and paginates.
