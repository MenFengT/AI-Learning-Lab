from agent import BuildingAgent



agent = BuildingAgent()



task = """

项目：
某住宅楼


建筑面积：
20000平方米


楼层：
20层


施工阶段：
主体施工


需求：

生成材料采购计划

"""



result = agent.run(task)



print("================")
print("建筑AI Agent报告")
print("================")

print(result)