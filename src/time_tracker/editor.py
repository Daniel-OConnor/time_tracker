import subprocess
import tempfile


def edit_string_in_vim(initial_content: str) -> str:
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
        temp_file.write(initial_content.encode())
        temp_file.flush()

        subprocess.run(["vim", temp_file.name])

        with open(temp_file.name, "rb") as temp2:
            edited_content = temp2.read().decode()

        return edited_content
