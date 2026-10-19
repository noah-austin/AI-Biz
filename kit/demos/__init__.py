"""Building blocks for the fictional demo companies.

Each demo lives in clients/<demo>/ with a profile (who the company is: branches, customers, products, people)
and a generate.py that uses these blocks to write what its systems would return on a given day, as JSON files
the demo connectors read. Everything is a pure function of the profile's seed and the as-of date, so the same
day always gives the same data, and moving the date forward plays the company forward.

    common.py    random numbers, calendars, seasons, names
    crm.py       sales reps, customer accounts and deals with their full history
    people.py    staff, licenses, timesheets and open roles (HR and payroll)
    stock.py     parts or products, locations, stock on hand and count corrections (inventory)
    buying.py    vendors and purchase orders (purchasing)
    writer.py    writes the files and the as-of date

Bluestem (clients/demo) predates these and still has its own generator.
"""
