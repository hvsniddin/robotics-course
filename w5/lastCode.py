import sys
import time
import random
import math

class Program():
  __interpretation_started_timestamp__ = time.time() * 1000

  pi = 3.141592653589793
  PWM = None
  st = None
  t = None
  theta_l = None

  def execMain(self):

    
    script.removeFile("motor_data.txt")
    
    self.PWM = 5
    
    while self.PWM >= 100:
      brick.encoder("E4").reset()
      
      brick.motor("M4").setPower(self.PWM)
      
      self.t = (time.time() * 1000 - self.__interpretation_started_timestamp__)
      
      while self.t < 2000:
        self.theta_l = brick.encoder("E4").read()
        self.t = (time.time() * 1000 - self.__interpretation_started_timestamp__)
        self.st = str(self.PWM) + "," + str(self.t) + "," + str(self.theta_l) + "\n"
        script.writeToFile("motor_data.txt", self.st)
        
        script.wait(5)
        
      brick.motor("M4").powerOff()
      
      script.wait(1000)
      
      self.PWM = self.PWM + 5
    brick.stop()
    return

def main():
  program = Program()
  program.execMain()

if __name__ == '__main__':
  main()
