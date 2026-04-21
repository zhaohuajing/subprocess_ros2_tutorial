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

    start_marker = "<<<BEGIN_JSON>>>"
    end_marker = "<<<END_JSON>>>"

    json_text = None
    start = result.stdout.find(start_marker)
    end = result.stdout.find(end_marker, start)
    if start != -1 and end != -1:
        json_text = result.stdout[start + len(start_marker):end].strip()
        print("Extracted JSON using markers.")
    else:
        for line in result.stdout.splitlines():
            if line.strip().startswith("{") and line.strip().endswith("}"):
                json_text = line.strip()
                break

    if json_text is None:
        preview = result.stdout[:500]
        raise RuntimeError(f"Inference did not return valid JSON. Preview:\n{preview}")

    return json_text


if __name__ == "__main__":
    scene_name = "scene_from_ucn"
    print(run_inference_in_docker(scene_name))
