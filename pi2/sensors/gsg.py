import time


def run_gsg_loop(delay, callback, stop_event, settings):
    
    from .MPU6050 import MPU6050
    mpu = MPU6050.MPU6050()
    mpu.dmp_initialize()
    while not stop_event.is_set():
        accel = mpu.get_acceleration()
        gyro = mpu.get_rotation()

        scaled_a = [x / 16384.0 for x in accel]
        scaled_g = [x / 131.0 for x in gyro]

        callback(scaled_a, scaled_g, settings)
        time.sleep(float(delay))
