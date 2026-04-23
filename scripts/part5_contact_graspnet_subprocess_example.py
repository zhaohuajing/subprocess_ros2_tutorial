#!/usr/bin/env python3
import subprocess

def run_inference_in_docker(scene_name: str) -> str:
    container_name = "contact_graspnet_container"
    np_path = f"test_data/{scene_name}.npy"

    compiled_lib = (
        "/root/graspnet_ws/src/contact_graspnet_ros2/contact_graspnet/"
        "pointnet2/tf_ops/sampling/tf_sampling_so.so"
    )

    compile_cmd = (
        f"if [ ! -f {compiled_lib} ]; then "
        f"cd /root/graspnet_ws/src/contact_graspnet_ros2/contact_graspnet && "
        f"conda run -n contact-graspnet bash compile_pointnet_tfops.sh; "
        f"fi"
    )

    inference_cmd = (
        "cd /root/graspnet_ws/src/contact_graspnet_ros2/contact_graspnet && "
        f"conda run -n contact-graspnet python contact_graspnet/inference.py "
        f"--np_path={np_path} --local_regions --filter_grasps"
    )

    cmd = [
        "docker", "exec", container_name,
        "bash", "-lc", f"{compile_cmd} && {inference_cmd}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Inference failed: {result.stderr}")

    return result.stdout


if __name__ == "__main__":
    print("This script shows the subprocess pattern used by the Contact-GraspNet ROS 2 wrapper.")
    print("Example usage inside a larger ROS 2 server:")
    print("    output = run_inference_in_docker('sample_scene')")
