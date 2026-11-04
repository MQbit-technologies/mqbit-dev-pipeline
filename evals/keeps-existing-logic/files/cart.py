def cart_total(items):
    total = 0
    for item in items:
        if item["qty"] < 0:
            raise ValueError("negative quantity")
        total += item["price"] * item["qty"]
    return total
