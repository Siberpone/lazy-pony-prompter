import launch
import os

req_file = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "requirements.txt"
)

if __name__ == "__main__":
    with open(req_file) as f:
        for package in f:
            try:
                package = package.strip()
                if not launch.is_installed(package):
                    launch.run_pip(
                        f"install {package}", f"lazy-pony-prompter: {package}"
                    )
            except Exception as e:
                print(e)
                print(
                    f'Warning: Failed to install {package}.'
                )
