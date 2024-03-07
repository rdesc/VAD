import numpy as np
import torch

from inference.runner import VADInferenceInput, VADInferenceOutput, VADRunner

CORRIDOR_WIDTH = 5  # meters
CORRIDOR_LENGTH = 10  # meters
CORRIDOR_START = 2.5  # meters
TTC = 2  # seconds


class BaselineVADRunner(VADRunner):
    def reset(self):
        super().reset()
        self.corridor_length = None
        self.stop_updating_corridor = False
        self.speed = None

    @torch.no_grad()
    def forward_inference(self, input: VADInferenceInput) -> VADInferenceOutput:
        output = super().forward_inference(input)
        if self.speed is None:
            self.speed = input.can_bus_signals[13]  # m/s
        target_speed = self.speed
        if len(output.aux_outputs.objects_in_bev) != 0:
            objects = np.array(
                output.aux_outputs.objects_in_bev
            )  # N x 5 (x, y, w, l, yaw) (y-forward, x-right)
            if not self.stop_updating_corridor:
                self.corridor_length = target_speed * TTC

            objects_in_corridor_long = np.logical_and(
                objects[:, 1] <= CORRIDOR_START + self.corridor_length,
                objects[:, 1] >= CORRIDOR_START,
            )
            objects_in_corridor = np.logical_and(
                objects_in_corridor_long,
                np.abs(objects[:, 0]) <= CORRIDOR_WIDTH / 2,
            )
            if np.any(objects_in_corridor):
                # break
                target_speed = 0.0  # m/s, set to low value, but not 0
                self.stop_updating_corridor = True

        trajectory = np.zeros((6, 2))
        trajectory[:, 1] = np.arange(1, 7) * target_speed / 2  # y-forward

        return VADInferenceOutput(
            trajectory=trajectory,
            aux_outputs=output.aux_outputs,
        )
