from helpers.string import shout
from helpers.math import area
message = "the area of a 5-by-8 rectangle is"
result = area(5, 8)
print(shout(f"{message} {result}"))