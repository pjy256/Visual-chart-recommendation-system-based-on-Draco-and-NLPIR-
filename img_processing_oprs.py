from IPython.display import display, Markdown
import draco as drc
import pandas as pd
from vega_datasets import data as vega_data
import altair as alt
from draco.renderer import AltairRenderer
import warnings
import os

warnings.filterwarnings("ignore")


# Suppressing warnings raised by altair in the background
# (iteration-related deprecation warnings)


def count_files_in_directory(directory_path):
    return len([name for name in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, name))])


# 推荐函数
def recommend_charts(
        spec: list[str], draco: drc.Draco, num: int = 5, labeler=lambda i: f"CHART {i + 1}"
) -> dict[str, dict]:
    # Dictionary to store the generated recommendations, keyed by chart name
    chart_specs = {}
    l=[]
    for i, model in enumerate(draco.complete_spec(spec, num*100)):
        if l:
            l.append(model)
            l.sort(key=lambda x: x.cost)
            if len(l) > num:
                l.pop()  
        else:
            l.append(model)

    for i, model in enumerate(l):
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
            chart = chart.configure_view(continuousWidth=130, continuousHeight=130)
        display(chart)
        chart.save(output_path + 'rec_ch' + str(count_files_in_directory(output_path)) + '.html')

    return chart_specs


#
def get_csvfile(file_path):
    df = pd.read_csv(file_path)
    return df


def get_jsonfile(file_path):
    df = pd.read_json(file_path)
    return df


def get_output_address():
    address = input("Please input the address where you want the picture to be output: ")
    return address


# 基础事实集的创建
def generate_spec_base(df):
    data_schema = drc.schema_from_dataframe(df)
    data_schema_facts = drc.dict_to_facts(data_schema)
    input_spec_base = data_schema_facts + [
        "entity(view,root,v0).",
        "entity(mark,v0,m0)."
    ]
    return input_spec_base


# 从更新的事实集中直接生成图表
# 用到了recommend函数
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
                # 暂时去掉
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
    # k = 0
    for cfg, spec in input_specs:
        # k += 1
        labeler = lambda i: f"CHART {i + 1} ({' | '.join(cfg)})"
        recs = recs | recommend_charts(spec=spec, draco=draco, num=num, labeler=labeler)

    return recs


# 生成饼图的输入函数
def get_users_restriction(df):
    print("Please input your restriction:")
    new_marks = input('marks:').split()
    polar = new_marks == ['pie']
    if polar:
        new_marks = []
    print(polar)
    if not new_marks:
        new_marks = ['point', 'bar', 'line', 'area', 'tick', 'rect'] if not polar else ['bar']
    new_fields = input('fields:').split()
    x_and_y = len(new_fields) == 3 and new_fields[1] == 'and'
    if x_and_y:
        new_fields.remove('and')
    if not new_fields:
        new_fields = df.columns.tolist()
    new_encoding_channels = input('new_encoding_channels:').split()
    if not new_encoding_channels:
        new_encoding_channels = ['color', 'shape', 'size', 'x', 'y'] if not polar else ['x']
        if x_and_y:
            new_encoding_channels = ['x', 'y']
    return [new_marks, new_fields, new_encoding_channels, polar]


# 用户输入约束条件的推荐函数
def update_spec(new_marks, new_fields, new_encoding_channels):
    recommendations = rec_from_generated_spec(
        marks=new_marks,
        fields=new_fields,
        encoding_channels=new_encoding_channels,
        draco=d,
    )
    # display_debug_data(draco=d, specs=recommendations)


# Parameterized helper to avoid code duplication as we iterate on designs
# 用于查看规范违反情况的函数
def display_debug_data(draco: drc.Draco, specs: dict[str, dict]):
    debugger = drc.DracoDebug(specs=specs, draco=draco)
    chart_preferences = debugger.chart_preferences
    display(Markdown("**Raw debug data**"))
    display(chart_preferences.head())

    display(Markdown("**Number of violated preferences**"))
    num_violations = len(
        set(chart_preferences[chart_preferences["count"] != 0]["pref_name"])
    )
    num_all = len(set(chart_preferences["pref_name"]))
    display(
        Markdown(
            f"*{num_violations} preferences are violated out of a total of {num_all} preferences (soft constraints)*"
        )
    )

    display(
        Markdown(
            "Using `DracoDebugPlotter` to visualize the debug `DataFrame` produced by `DracoDebug`:"
        )
    )
    plotter = drc.DracoDebugPlotter(chart_preferences)
    plot_size = (600, 300)
    chart = plotter.create_chart(
        cfg=drc.DracoDebugChartConfig.SORT_BY_COUNT_SUM,
        violated_prefs_only=True,
        plot_size=plot_size,
    )
    chart.save(output_path + 'debugchart' + str(count_files_in_directory(output_path)) + '.html')


path = input("Please input the path of the csv file: ")
output_path = get_output_address() + '\\'
df = get_csvfile(path)
d = drc.Draco()
renderer = AltairRenderer()
input_spec_base = generate_spec_base(df)
# recommendations = recommend_charts(spec=input_spec_base, draco=d, num=5)
# display_debug_data(draco=d, specs=recommendations)
n_marks, n_fields, n_encoding_channels, polar = get_users_restriction(df)
print(n_marks, n_fields, n_encoding_channels, polar)
if polar:
    input_spec_base.append('attribute((view,coordinates),v0,polar).')
update_spec(n_marks, n_fields, n_encoding_channels)
# display_debug_data(draco=d, specs=recommendations)
# C:\Users\27217\Documents\GitHub\testing-7-16-23\laofan\data\weather.csv
# C:\Users\27217\Desktop\testing generate charts
# point line bar
# weather wind date
