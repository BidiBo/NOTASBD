:: setup.bat
@echo off
echo Instalando dependencias del Bot de Notas...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Todo listo. Usa run.bat para iniciar.
pause