pushd .
cd /home/jmatthews/git/jwmatthews/tinkering/aws/reporting
source venv/bin/activate
python ./write_instance_report.py
deactivate
popd


