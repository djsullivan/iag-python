import json


class Prints():
  '''
    Closs to provide logging infrastructure for install scripts
  '''

  def __init__(self, start=1):
    self.step = int(start)

  def prints(self, data, indent=1):
    print(indent * '   ' + data)

  def json(self, data, indent=1):
    print("   " * indent + data.replace('\n', '\n' + "   " * indent))
  
  def task(self, data, indent=1):
    print('\n' + indent * '   ' + f"({self.step}) " + data + "\n")
    self.step = self.step + 1