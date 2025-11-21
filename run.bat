@echo off

set arg1=%1
set program_name=eflash_reader

if not exist ".venv" (

    echo The .venv folder doesn't exists, creating virtual environment
    python -m venv .venv

    echo Installing pipenv in created virtual environment
    call .venv\Scripts\activate
    pip install pipenv

    echo Installing dependencies using pipenv
    pipenv install

) else (
    echo The .venv folder exists
    call .venv\Scripts\activate
)


echo Running %program_name% program in local environment
pipenv run python %program_name%.py %arg1% 
echo %program_name% program exited, operation completed