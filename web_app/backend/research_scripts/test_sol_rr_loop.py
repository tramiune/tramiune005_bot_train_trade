import subprocess
for rr in [3.0, 4.0, 5.0, 7.0, 10.0]:
    cmd = f"sed -i '' 's/rr_target = .*/rr_target = {rr}/g' test_sol_retest_filtered.py"
    subprocess.run(cmd, shell=True)
    out = subprocess.check_output("source .venv/bin/activate && python3 test_sol_retest_filtered.py | tail -n 6", shell=True)
    print(f"--- RR {rr} ---")
    print(out.decode())
