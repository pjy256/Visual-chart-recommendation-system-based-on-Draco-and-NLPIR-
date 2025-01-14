
# Suppressing warnings raised by altair in the background
# (iteration-related deprecation warnings)
from draco import dict_to_facts, answer_set_to_dict, run_clingo
import warnings
from draco.renderer import AltairRenderer
warnings.filterwarnings("ignore")
# Display utilities
from pprint import pprint
from IPython.display import display, Markdown
import draco as drc
import pandas as pd
from vega_datasets import data as vega_data
import altair as alt
d = drc.Draco()
renderer = AltairRenderer()
charts=[]
#载入数据


def load_data(file_path):
    df=pd.read_csv(file_path)
    return df

#基础事实集的创建
def generate_spec_base(df):
    data_schema = drc.schema_from_dataframe(df)
    data_schema_facts = drc.dict_to_facts(data_schema)
    input_spec_base = data_schema_facts + [
        "entity(view,root,v0).",
        "entity(mark,v0,m0)."
    ]
    return input_spec_base



#推荐图表生成函数
def recommend_charts(
    spec: list[str], draco: drc.Draco, num: int = 5, labeler=lambda i: f"CHART {i+1}",k:int =1
) -> dict[str, dict]:
    # Dictionary to store the generated recommendations, keyed by chart name
    print('running')
    chart_specs = {}
    for i, model in enumerate(draco.complete_spec(spec, num)):
        if model.cost[0]>40:
            continue
        chart_name = labeler(i)
        spec = drc.answer_set_to_dict(model.answer_set)
        chart_specs[chart_name] = drc.dict_to_facts(spec)

        print(chart_name)
        print(f"COST: {model.cost}")
        chart = renderer.render(spec=spec, data=df)
        # Adjust column-faceted chart size
        if (
            isinstance(chart, alt.FacetChart)
            and chart.facet.column is not alt.Undefined
        ):
            #print('nihao'*10)
            chart = chart.configure_view(continuousWidth=130, continuousHeight=130)
        display(chart)
        charts.append([chart.copy(),model.cost[0]])
        #chart.save('D:\\testoutput\\'+'chart'+str(k+i)+'.html')

    return chart_specs

#添加约束条件
def rec_from_generated_spec(
    marks: list[str],
    fields: list[str],
    encoding_channels: list[str],
    draco: drc.Draco,
    num: int = 1,
) -> dict[str, dict]:
    input_specs = [
        (
            (mark, field, enc_ch),
            input_spec_base
            + [
                f"attribute((mark,type),m0,{mark}).",
                "entity(encoding,m0,e0).",
                f"attribute((encoding,field),e0,{field}).",
                f"attribute((encoding,channel),e0,{enc_ch}).",
                # filter out designs with less than 3 encodings
                ":- {entity(encoding,_,_)} < 3.",
                # exclude multi-layer designs
                ":- {entity(mark,_,_)} != 1.",
            ],
        )
        for mark in marks
        for field in fields
        for enc_ch in encoding_channels
    ]
    recs = {}
    k=0
    for cfg, spec in input_specs:
        k+=1
        labeler = lambda i: f"CHART {i + 1} ({' | '.join(cfg)})"
        recs = recs | recommend_charts(spec=spec, draco=draco, num=num, labeler=labeler,k=k)

    return recs
#用户输入约束条件

def update_spec(new_marks,new_fields,new_encoding_channels):
    recommendations = rec_from_generated_spec(
        marks=new_marks,
        fields=new_fields,
        encoding_channels=new_encoding_channels,
        draco=d,
    )
##########################################################################################################


file_path=input("数据地址:")
if file_path=='':
    file_path='data\\weather.csv'
df=load_data(file_path)
#df=load_data('data\\test.csv')
header=df.columns.tolist()
input_spec_base=generate_spec_base(df)
polar=0
x_and_y=0
categorical=1

#recommend_charts(input_spec_base,draco=d)
print("约束条件:")

new_marks=input('marks:').split()
if new_marks==['pie']:
    polar=1
    new_marks=[]
if polar:
    input_spec_base+=['attribute((view,coordinates),v0,polar).']
if categorical:
    input_spec_base += [
    'entity(scale,v0,7).',
    'attribute((scale,channel),7,color).',
    'attribute((scale,type),7,categorical).'
        ]
if len(new_marks)==0:
    new_marks=['point','bar','line','area','tick','rect'] if not polar else ['bar']

new_fields=input('fields:').split()
if len(new_fields)==3 and new_fields[1]=='and':
    new_fields.remove(new_fields[1])
    x_and_y=1
if len(new_fields)==0:
    new_fields=header

new_encoding_channels=input('new_encoding_channels:').split()
if len(new_encoding_channels)==0:
    new_encoding_channels=['color','shape','size','x','y'] if not polar else ['x']
    if x_and_y:
        new_encoding_channels=['x','y']
print(new_marks,'\n',new_fields,'\n',new_encoding_channels)
update_spec(new_marks,new_fields,new_encoding_channels)


charts=sorted(charts,key= lambda x:x[1])
for i in range(len(charts)):
    charts[i][0].save('D:\\testoutput\\'+'chart'+str(i)+'.html')

def pie_spec(field_name):
    n=field_name
    spec=[
        'attribute(number_rows,root,20000).',
        f'entity(field,root,{n}).',
        f'attribute((field,name),{n},{n}).',
        f'attribute((field,type),{n},string).',
        'entity(view,root,0).',
        'attribute((view,coordinates),0,polar).',
        'entity(mark,0,1).',
        'attribute((mark,type),1,bar).',
        'entity(encoding,1,2).',
        'attribute((encoding,channel),2,y).',
        'attribute((encoding,aggregate),2,count).',
        'attribute((encoding,stack),2,zero).',
        'entity(encoding,1,3).',
        'attribute((encoding,channel),3,color).',
        f'attribute((encoding,field),3,{n}).'
    ]
    return spec
def generate_by_spec(spec):
    for model in run_clingo(spec):
         answer_set = model.answer_set
         dic = drc.answer_set_to_dict(answer_set)
         chart=renderer.render(dic,df)
         chart.save('output_path')

#绘制径向图
def radial_spec(file_name,value):
    n= file_name
    c=value
    spec=['attribute(number_rows,root,20000).',
     f'entity(field,root,{c}).',
     f'attribute((field,name),{c},{c}).',
     f'attribute((field,type),{c},number).',
     f'entity(field,root,{n}).',
     f'attribute((field,name),{n},{n}).',
     f'attribute((field,type),{n},string).',
     'entity(view,root,0).',
     'attribute((view,coordinates),0,polar).',
     'entity(mark,0,1).',
     'attribute((mark,type),1,bar).',
     'entity(encoding,1,2).',
     'attribute((encoding,channel),2,x).',
     f'attribute((encoding,field),2,{n}).',
     'entity(encoding,1,3).',
     'attribute((encoding,channel),3,y).',
     f'attribute((encoding,field),3,{c}).',
     'attribute((encoding,aggregate),3,mean).',
     'entity(scale,0,4).',
     'attribute((scale,channel),4,x).',
     'attribute((scale,type),4,ordinal).',
     'entity(scale,0,5).',
     'attribute((scale,channel),5,y).',
     'attribute((scale,type),5,linear).',
     'attribute((scale,zero),5,true).']
    return spec


