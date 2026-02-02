# Digital-Health-Literacy-Companion-Tool-Lakeland-Regional-Health-
This project aims to develop a digital health literacy companion that replaces generic discharge handouts with interactive, patient-specific guidance. It will use clear language, multimedia, and offer reminders or follow-up support. It must be usable by patients with low digital literacy and integrate with existing hospital systems.


How to deploy the Django server:
1. Clone the repository
2. Git pull if needed
3. Go to the HealthFront directory in Powershell
4. Create the virtual environment
5. Bypass restrictions
6. Activate virtual environment
7. Install Django
8. Run database migrations
9. Run the server
10. Go to the address that's listed

git switch frontend-login-zaina
cd .\Frontend\django\HealthFront
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   
venv\Scripts\activate
pip install Django
python manage.py migrate
python manage.py runserver


