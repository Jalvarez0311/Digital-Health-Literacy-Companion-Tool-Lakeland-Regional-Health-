# Digital-Health-Literacy-Companion-Tool-Lakeland-Regional-Health-
This project aims to develop a digital health literacy companion that replaces generic discharge handouts with interactive, patient-specific guidance. It will use clear language, multimedia, and offer reminders or follow-up support. It must be usable by patients with low digital literacy and integrate with existing hospital systems.


How to deploy the Django server:
1. Clone the repository
2. git switch frontend-login-zaina                              // (and git pull if needed)
3. cd .\Frontend\django\HealthFront
4. python -m venv venv                                          // (to create the virtual environment)
5. Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   // (in Powershell, if needed)
6. venv\Scripts\activate                                        // (to activate the virtual environment)
7. pip install Django
8. python manage.py migrate                                     // (run database migrations)
9. python manage.py runserver                                   // (to run the server)
10. Finally, go to the address that's listed saying "Starting development server at XXXXXXXXXX"
