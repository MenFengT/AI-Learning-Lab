from agent import BuildingAgent



# 创建Agent

agent = BuildingAgent()



# 调用材料计算工具

material_plan = agent.calculate_material_plan(

    area=20000,

    floors=20

)



print("=====材料计算结果=====")


print(material_plan)



# 再让AI整理输出

result = agent.run(

"""
项目：

某住宅楼


工程信息：

建筑面积：
20000平方米


楼层：

20层


施工阶段：

主体施工阶段


请根据材料计算结果，
生成材料采购计划。

"""

)



print("\n=====AI生成报告=====")


print(result)