import subprocess
import keyring

# Run this code with the password of user pi of the RaspberryPi
# keyring.set_password("master_pi", "pi", "***********")

def run(cmd : str, print_cmd=False) -> subprocess.CompletedProcess[bytes]:

    if(print_cmd):
        print("Running command:")
        print(cmd.replace("; ", "\n"))

    completed = subprocess.run(["powershell", "-Command", cmd], capture_output=True)
    
    if completed.returncode != 0:
        print("An error occurred: %s", completed.stderr.decode())
    else:
        print("Command executed successfully!")
        print(completed.stdout.decode())

    return completed


def download(src : str, dest_dir : str, relative=True, password : str = None) -> subprocess.CompletedProcess[bytes]:

    if password is None:
        password = keyring.get_password("master_pi", "pi")

    if(relative):
        command =  "$currentDir = Get-Location; \
                    $targetDir = $utilsDir  = Join-Path -Path $currentDir -ChildPath '%s'; \
                    pscp -pw %s -P 22 pi@MasterarbeitPi:%s $targetDir" % (password, dest_dir, src)
        
        return run(command)
    else:
        print("currently not supported!")
        return None


def upload(src_dir : str, src : str, dest_dir : str, relative=True, password : str = None) -> subprocess.CompletedProcess[bytes]:

    # imput check
    if(len(src) == 0):
        print("Error: no source file specified")
        return None
    elif(not src.__contains__(".")):
        print("Error: not a valid source file")
        return None
    
    if password is None:
        password = keyring.get_password("master_pi", "pi")

    if(relative):
        command = "cd '%s'; pscp -pw %s %s pi@MasterarbeitPi:%s" % (src_dir, password, src, dest_dir)
        return run(command)
    else:
        print("currently not supported!")
        return None