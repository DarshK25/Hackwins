"""
Generate gRPC Python code from proto files.
Run this script after adding/modifying .proto files.
"""
import os
import sys
from pathlib import Path

# Add the ai-gateway directory to path
sys.path.insert(0, str(Path(__file__).parent))

def generate_grpc_code():
    """Generate Python gRPC code from proto files."""
    proto_dir = Path(__file__).parent / "app" / "grpc" / "proto"
    output_dir = Path(__file__).parent / "app" / "grpc" / "gen"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all .proto files
    proto_files = list(proto_dir.glob("*.proto"))
    if not proto_files:
        print(f"No .proto files found in {proto_dir}")
        return

    for proto_file in proto_files:
        print(f"Compiling {proto_file.name}...")

        # Command to generate Python gRPC code
        cmd = (
            f"python -m grpc_tools.protoc "
            f"-I{proto_dir} "
            f"--python_out={output_dir} "
            f"--grpc_python_out={output_dir} "
            f"{proto_file}"
        )

        print(f"Running: {cmd}")
        os.system(cmd)

    # Create __init__.py files
    init_files = [
        output_dir / "__init__.py",
        output_dir.parent / "__init__.py",
    ]

    for init_file in init_files:
        if not init_file.exists():
            init_file.touch()
            print(f"Created {init_file}")

    print("gRPC code generation complete!")
    print(f"Generated files are in: {output_dir}")


if __name__ == "__main__":
    generate_grpc_code()
