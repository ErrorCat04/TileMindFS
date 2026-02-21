
import time

class Optimizer:
    def run_loop(self, interval=5):
        print("Optimizer running (Ctrl+C to stop)")
        try:
            while True:
                print("Optimization tick...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Optimizer stopped.")
