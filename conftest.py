
def pytest_exception_interact(node, call, report):
    """It would be cool to catch snapshot errors here and show an image diff viewer popup with the before and after"""
    # if report.failed:
    #     with open('report.txt', 'w+') as f:
    #         f.write(report)
