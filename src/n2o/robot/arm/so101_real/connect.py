from .lerobot_robot_so101_5dof import SO101Follower5Dof, SO101Follower5DofConfig


def connect_so101(
    port,
    *,
    id="n2o_so101_5dof",
    calibrate=False,
    max_relative_target=2.0,
    disable_torque_on_disconnect=True,
    **config_kwargs,
):
    """Build, connect, and return a `SO101Follower5Dof` for `port` -- a thin
    convenience wrapper over `SO101Follower5DofConfig`/`SO101Follower5Dof` so a caller
    doesn't have to construct the config by hand just to pass a port.

    `max_relative_target`/`disable_torque_on_disconnect` default to the same
    conservative values `examples/09_real_so101_arm_control.ipynb` uses. `calibrate`
    stays `False` by default -- calibration needs real stdin (incompatible with being
    driven from inside a library call from a notebook kernel) and is a one-time step;
    run `uv run lerobot-calibrate --robot.type=so101_follower_5dof --robot.port=<port>
    --robot.id=<id>` in a real terminal first, then this raises `RuntimeError` if that
    calibration file still doesn't exist. Extra **config_kwargs (e.g. `cameras=...`,
    `use_degrees=...`) are forwarded to `SO101Follower5DofConfig`.
    """
    config = SO101Follower5DofConfig(
        port=port,
        id=id,
        max_relative_target=max_relative_target,
        disable_torque_on_disconnect=disable_torque_on_disconnect,
        **config_kwargs,
    )
    arm = SO101Follower5Dof(config)
    if not calibrate and not arm.calibration_fpath.is_file():
        raise RuntimeError(
            f"no calibration file at {arm.calibration_fpath} -- run "
            f"`uv run lerobot-calibrate --robot.type=so101_follower_5dof "
            f"--robot.port={port} --robot.id={id}` in a real terminal first, then "
            "call connect_so101() again"
        )
    arm.connect(calibrate=calibrate)
    return arm
