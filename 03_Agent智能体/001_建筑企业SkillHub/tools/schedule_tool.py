from datetime import datetime


def generate_months(start_date, end_date):

    """
    根据开始结束日期生成月份列表

    例如：

    2026-03-16
    2026-10-30

    返回：

    [
    "2026-03",
    "2026-04",
    ...
    ]

    """


    start = datetime.strptime(
        start_date,
        "%Y-%m-%d"
    )


    end = datetime.strptime(
        end_date,
        "%Y-%m-%d"
    )


    months=[]


    current = start.replace(
        day=1
    )


    while current <= end:


        month = current.strftime(
            "%Y-%m"
        )


        months.append(
            month
        )


        if current.month == 12:

            current = current.replace(

                year=current.year+1,

                month=1

            )

        else:

            current=current.replace(

                month=current.month+1

            )


    return months