import xml.etree.ElementTree as ET

def analyze_svg_structure(element, indent=''):
    """
    递归打印出 SVG 元素的结构，以便分析。
    """
    # 清理标签名，去除命名空间（例如 {http://www.w3.org/2000/svg}svg -> svg）
    tag = element.tag.split('}')[-1]
    
    print(f"{indent}Tag: <{tag}>, Attributes: {element.attrib}")
    
    for child in element:
        analyze_svg_structure(child, indent + '  ')

def add_svg_annotation(root, x, y, text_label="Heart"):
    """
    在 SVG 的根元素中添加一个标注（一个圆圈和一个文本标签）。
    
    参数:
    - root: SVG 的根元素 (ElementTree object)
    - x: 标注的 X 坐标
    - y: 标注的 Y 坐标
    - text_label: 要显示的文本
    """
    
    # 创建一个新的组 <g> 来容纳我们的标注
    # 给予一个唯一的 ID，方便识别
    annotation_group = ET.Element('g', id="heart-annotation")
    
    # 创建一个红色的圆圈 <circle>
    # cx, cy 是圆心的坐标
    # r 是半径
    circle = ET.Element('circle', {
        'cx': str(x),
        'cy': str(y),
        'r': '10',  # 半径为10个单位（您可以按需调整）
        'fill': 'red',
        'opacity': '0.7' # 70% 透明度
    })
    
    # 创建一个文本标签 <text>
    # x, y 是文本的起始坐标
    text = ET.Element('text', {
        'x': str(x + 15),  # X 坐标向右偏移15个单位，以免与圆圈重叠
        'y': str(y + 5),   # Y 坐标向下偏移5个单位，使其与圆圈中心对齐
        'fill': 'black',
        'font-size': '12',
        'font-family': 'Arial, sans-serif'
    })
    text.text = text_label  # 设置文本内容

    # 将圆圈和文本添加到组中
    annotation_group.append(circle)
    annotation_group.append(text)
    
    # 将整个标注组添加到 SVG 的根元素中
    root.append(annotation_group)
    print(f"\n成功添加标注 '{text_label}' 在坐标 ({x}, {y})")


def main():
    # --- 您需要配置的参数 ---
    
    # 1. 输入的 SVG 文件名
    input_svg_file = 'tongyong.svg'  # <--- 请修改为您 SVG 文件的路径
    
    # 2. 输出的 SVG 文件名
    output_svg_file = 'tongyong2.svg'
    
    # 3. 标注的坐标 (x, y) 和标签
    # !!! 您需要根据 SVG 的坐标系来调整这些值 !!!
    ANNOTATION_X = 150 
    ANNOTATION_Y = 200
    ANNOTATION_LABEL = "Heart (心脏)"
    
    # -----------------------------
    
    try:
        # 注册 SVG 命名空间，这对于正确解析和保存至关重要
        # （'': 'http://www.w3.org/2000/svg' 表示这是默认命名空间）
        ET.register_namespace('', 'http://www.w3.org/2000/svg')

        # 解析 SVG 文件
        tree = ET.parse(input_svg_file)
        root = tree.getroot()

        # 1. 分析并打印结构
        print(f"--- 正在分析 SVG 结构: {input_svg_file} ---")
        analyze_svg_structure(root)
        print("-------------------------------------------------")

        # 2. 添加标注
        add_svg_annotation(root, ANNOTATION_X, ANNOTATION_Y, ANNOTATION_LABEL)

        # 3. 保存修改后的文件
        # encoding='utf-8' 和 xml_declaration=True 确保文件格式正确
        tree.write(output_svg_file, encoding='utf-8', xml_declaration=True)
        print(f"成功创建已标注的文件: {output_svg_file}")

    except FileNotFoundError:
        print(f"错误: 找不到输入文件 '{input_svg_file}'。")
        print("请确保文件名正确，并且文件与脚本在同一目录下。")
    except ET.ParseError as e:
        print(f"错误: 解析 SVG 文件失败。文件可能已损坏或不是有效的 XML。 {e}")
    except Exception as e:
        print(f"发生意外错误: {e}")

if __name__ == "__main__":
    main()