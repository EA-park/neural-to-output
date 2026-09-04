# Camera

`robot/camera/` is still an empty placeholder — no concrete
[`Part`](../index.md#the-part-interface) implementation exists yet (see
`ROADMAP.md`). Once a camera driver is added, it'll follow the same shape as
`arm`/`hand`: a `Part` subclass under `robot/camera/`, re-exported from
`robot/camera/__init__.py`.

A camera is meant to feed
[`ControllerType.VLA`](../index.md#controllertype-and-routing) (vision-language-action)
routing eventually — also not implemented yet.
