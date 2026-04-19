# Digital-Health-Literacy-Companion-Tool-Lakeland-Regional-Health-
This project aims to develop a digital health literacy companion that replaces generic discharge handouts with interactive, patient-specific guidance. It will use clear language, multimedia, and offer reminders or follow-up support. It must be usable by patients with low digital literacy and integrate with existing hospital systems.


How to deploy the Django server:
1. Clone the repository
2. Git pull if needed (git switch XXX)
3. Go to the HealthFront directory in Powershell
4. Create the virtual environment
5. Bypass restrictions
6. Activate virtual environment
7. Install Django
8. Run database migrations
9. Run the server
10. Go to the address that's listed

```
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd .\django\HealthFront
pip install django
python manage.py migrate
python manage.py runserver

```
