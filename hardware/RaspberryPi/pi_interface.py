import subprocess
import keyring

user_name : str = "pi"
raspberry_name : str = "RaspberryPi"

def set_user(usr : str):
    global user_name
    user_name = usr


def set_raspberry_name(name : str):
    global raspberry_name
    raspberry_name = name


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
                    pscp -pw %s -P 22 %s@%s:%s $targetDir" % (password, dest_dir, user_name, raspberry_name, src)
        
        return run(command)
    else:
        print("currently not supported!")
        return None


def upload(src_dir : str, src : str, dest_dir : str, relative=True, password : str = None) -> subprocess.CompletedProcess[bytes]:

    global user_name, raspberry_name
    # input check
    if(len(src) == 0):
        print("Error: no source file specified")
        return None
    elif(not src.__contains__(".")):
        print("Error: not a valid source file")
        return None
    
    if password is None:
        password = keyring.get_password("master_pi", "pi")

    if(relative):
        command = "cd '%s'; pscp -pw %s %s %s@%s:%s" % (src_dir, password, src, user_name, raspberry_name, dest_dir)
        return run(command)
    else:
        print("currently not supported!")
        return None