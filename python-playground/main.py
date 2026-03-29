# Fib counter using python
    # n is the number of times to iterate through the sequence
    # seed with f0 = 0 and f1 = 1
    # sequence goes 0,1,2,3,5,8,13,21

f_0 = 0
f_1 = 1

print("Fibonacci Sequence Counter n times")
print("How many times would you like to run this?")
n = 1000
print("Now running ")
print(n)
print("times")
for x in range(n):
    fib_next = f_0 + f_1
    f_0 = f_1
    f_1 = fib_next
    print(fib_next)



