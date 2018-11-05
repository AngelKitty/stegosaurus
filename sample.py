"""Example carrier file to embed our payload in.
"""

from math import sqrt


def fib_v1(n):
    if n == 0 or n == 1:
        return n
    return fib_v1(n - 1) + fib_v1(n - 2)


def fib_v2(n):
    if n == 0 or n == 1:
        return n
    return int(((1 + sqrt(5))**n - (1 - sqrt(5))**n) / (2**n * sqrt(5)))


def main():
    result1 = fib_v1(12)
    result2 = fib_v2(12)

    print(result1)
    print(result2)

if __name__ == "__main__":
    main()
