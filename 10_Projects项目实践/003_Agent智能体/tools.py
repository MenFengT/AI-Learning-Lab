def calculate_material(
        area,
        floors
):

    """
    建筑主体材料估算工具

    area:
        建筑面积 ㎡

    floors:
        建筑层数

    """

    # 混凝土经验系数
    concrete = area * 0.45


    # 钢筋经验系数
    steel = area * 0.055


    # 模板经验系数
    template = area * 3



    return {

        "混凝土":
            f"{round(concrete,2)} m³",

        "钢筋":
            f"{round(steel,2)} 吨",

        "模板":
            f"{round(template,2)} ㎡"

    }