"""Demo shop: add prices and print a total."""

PRICES = {"bread": 2, "milk": 3}


def total(items):
    return sum(PRICES[item] for item in items)


if __name__ == "__main__":
    print(total(["bread", "milk"]))
