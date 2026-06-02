import wbdata
# import inspect
# print(inspect.signature(wbdata.get_country))

countries = wbdata.get_country(source=2)

print(countries)
