import os
from pathlib import Path

os.environ['no_proxy'] = '*' # 避免代理网络产生意外污染

help_menu_description = \
"""cloud micro"""

def main():
    import gradio as gr
    # if gr.__version__ not in ['3.32.8']:
    #     raise ModuleNotFoundError("使用项目内置Gradio获取最优体验! 请运行 `pip install -r requirements.txt` 指令安装内置Gradio及其他依赖, 详情信息见requirements.txt.")
    from request_llms.bridge_all import predict
    from toolbox import format_io, find_free_port, on_file_uploaded, on_report_generated, get_conf, ArgsGeneralWrapper, load_chat_cookies, DummyWith
    # 建议您复制一个config_private.py放自己的秘密, 如API和代理网址
    proxies, WEB_PORT, LLM_MODEL, CONCURRENT_COUNT, AUTHENTICATION = get_conf('proxies', 'WEB_PORT', 'LLM_MODEL', 'CONCURRENT_COUNT', 'AUTHENTICATION')
    CHATBOT_HEIGHT, LAYOUT, AVAIL_LLM_MODELS, AUTO_CLEAR_TXT = get_conf('CHATBOT_HEIGHT', 'LAYOUT', 'AVAIL_LLM_MODELS', 'AUTO_CLEAR_TXT')
    ENABLE_AUDIO, AUTO_CLEAR_TXT, PATH_LOGGING, AVAIL_THEMES, THEME, ADD_WAIFU = get_conf('ENABLE_AUDIO', 'AUTO_CLEAR_TXT', 'PATH_LOGGING', 'AVAIL_THEMES', 'THEME', 'ADD_WAIFU')
    DARK_MODE, NUM_CUSTOM_BASIC_BTN, SSL_KEYFILE, SSL_CERTFILE = get_conf('DARK_MODE', 'NUM_CUSTOM_BASIC_BTN', 'SSL_KEYFILE', 'SSL_CERTFILE')
    INIT_SYS_PROMPT = get_conf('INIT_SYS_PROMPT')

    # 是否显示所有功能界面
    is_show_all_function = False
    title_desc = get_conf('TITLE_DESC')
    if not title_desc:
        title_desc = 'GPT 学术优化'

    # 如果WEB_PORT是-1, 则随机选取WEB端口
    PORT = find_free_port() if WEB_PORT <= 0 else WEB_PORT
    from check_proxy import get_current_version
    from themes.theme import adjust_theme, advanced_css, theme_declaration, js_code_clear, js_code_reset, js_code_show_or_hide, js_code_show_or_hide_group2
    from themes.theme import js_code_for_css_changing, js_code_for_toggle_darkmode, js_code_for_persistent_cookie_init
    from themes.theme import load_dynamic_theme, to_cookie_str, from_cookie_str, init_cookie
    # title_html = f"<h1 align=\"center\">{title_desc} {get_current_version()}</h1>{theme_declaration}"
    title_html = f"<h1 align=\"center\">{title_desc} </h1>{theme_declaration}"
    help_menu_description = f"{title_desc} 1.0 "

    # 问询记录, python 版本建议3.9+（越新越好）
    import logging, uuid
    os.makedirs(PATH_LOGGING, exist_ok=True)
    try:logging.basicConfig(filename=f"{PATH_LOGGING}/chat_secrets.log", level=logging.INFO, encoding="utf-8", format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    except:logging.basicConfig(filename=f"{PATH_LOGGING}/chat_secrets.log", level=logging.INFO,  format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    # Disable logging output from the 'httpx' logger
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print(f"所有问询记录将自动保存在本地目录./{PATH_LOGGING}/chat_secrets.log, 请注意自我隐私保护哦！")

    # 一些普通功能模块
    from core_functional import get_core_functions
    functional = get_core_functions()

    # 高级函数插件
    from crazy_functional import get_crazy_functions
    DEFAULT_FN_GROUPS = get_conf('DEFAULT_FN_GROUPS')
    plugins = get_crazy_functions()
    # 遍历每个插件配置的Group字段，并把Group字段的值用'|'分割，组成列表
    all_plugin_groups = list(set([g for _, plugin in plugins.items() for g in plugin['Group'].split('|')]))
    # tags中的任一个元素是否在groups里
    match_group = lambda tags, groups: any([g in groups for g in tags.split('|')])

    # 处理markdown文本格式的转变
    gr.Chatbot.postprocess = format_io

    # 做一些外观色彩上的调整
    set_theme = adjust_theme()

    # 代理与自动更新
    from check_proxy import check_proxy, auto_update, warm_up_modules
    proxy_info = check_proxy(proxies)

    gr_L1 = lambda: gr.Row().style()
    gr_L2 = lambda scale, elem_id: gr.Column(scale=scale, elem_id=elem_id, min_width=400)
    if LAYOUT == "TOP-DOWN":
        gr_L1 = lambda: DummyWith()
        gr_L2 = lambda scale, elem_id: gr.Row()
        CHATBOT_HEIGHT /= 2

    cancel_handles = []
    customize_btns = {}
    predefined_btns = {}

    #ui
    file_upload_2 = None
    with gr.Blocks(title=title_desc, theme=set_theme, analytics_enabled=False, css=advanced_css) as demo:
        gr.HTML(title_html)
        secret_css, dark_mode, py_pickle_cookie = gr.Textbox(visible=False), gr.Textbox(DARK_MODE, visible=False), gr.Textbox(visible=False)
        cookies = gr.State(load_chat_cookies())
        with gr_L1():
            with gr_L2(scale=2, elem_id="gpt-chat"):
                chatbot = gr.Chatbot(label=f"当前模型：{LLM_MODEL}", elem_id="gpt-chatbot")
                if LAYOUT == "TOP-DOWN":  chatbot.style(height=CHATBOT_HEIGHT)
                history = gr.State([])
            with gr_L2(scale=1, elem_id="gpt-panel"):
                with gr.Accordion("输入区", open=True, elem_id="input-panel") as area_input_primary:
                    with gr.Row():
                        txt = gr.Textbox(show_label=False, placeholder="请在这里输入你想问的问题...", elem_id='user_input_main').style(container=False)
                    with gr.Row():
                        submitBtn = gr.Button("提交", elem_id="elem_submit", variant="primary")
                    with gr.Row():
                        resetBtn = gr.Button("重置", elem_id="elem_reset", variant="secondary"); resetBtn.style(size="sm")
                        stopBtn = gr.Button("停止", elem_id="elem_stop", variant="secondary"); stopBtn.style(size="sm")
                        clearBtn = gr.Button("清除", elem_id="elem_clear", variant="secondary", visible=False); clearBtn.style(size="sm")
                    if ENABLE_AUDIO:
                        with gr.Row():
                            audio_mic = gr.Audio(source="microphone", type="numpy", elem_id="elem_audio", streaming=True, show_label=False).style(container=False)
                    with gr.Row():
                        status = gr.Markdown(f"Tip: 按Enter提交, 按Shift+Enter换行。当前模型: {LLM_MODEL} \n {proxy_info}", elem_id="state-panel")

                with gr.Accordion("基础功能区", open=True, elem_id="basic-panel", render=is_show_all_function) as area_basic_fn:
                    with gr.Row():
                        for k in range(NUM_CUSTOM_BASIC_BTN):
                            customize_btn = gr.Button("自定义按钮" + str(k+1), visible=False, variant="secondary", info_str=f'基础功能区: 自定义按钮')
                            customize_btn.style(size="sm")
                            customize_btns.update({"自定义按钮" + str(k+1): customize_btn})
                        for k in functional:
                            if ("Visible" in functional[k]) and (not functional[k]["Visible"]): continue
                            variant = functional[k]["Color"] if "Color" in functional[k] else "secondary"
                            functional[k]["Button"] = gr.Button(k, variant=variant, info_str=f'基础功能区: {k}')
                            functional[k]["Button"].style(size="sm")
                            predefined_btns.update({k: functional[k]["Button"]})
                with gr.Accordion("函数插件区", open=True, elem_id="plugin-panel", render=is_show_all_function) as area_crazy_fn:
                    with gr.Row():
                        gr.Markdown("插件可读取“输入区”文本/路径作为参数（上传文件自动修正路径）")
                    with gr.Row(elem_id="input-plugin-group"):
                        plugin_group_sel = gr.Dropdown(choices=all_plugin_groups, label='', show_label=False, value=DEFAULT_FN_GROUPS,
                                                      multiselect=True, interactive=True, elem_classes='normal_mut_select').style(container=False)
                    with gr.Row():
                        for k, plugin in plugins.items():
                            if not plugin.get("AsButton", True): continue
                            visible = True if match_group(plugin['Group'], DEFAULT_FN_GROUPS) else False
                            variant = plugins[k]["Color"] if "Color" in plugin else "secondary"
                            info = plugins[k].get("Info", k)
                            plugin['Button'] = plugins[k]['Button'] = gr.Button(k, variant=variant,
                                visible=visible, info_str=f'函数插件区: {info}').style(size="sm")
                    with gr.Row():
                        with gr.Accordion("更多函数插件", open=True):
                            dropdown_fn_list = []
                            for k, plugin in plugins.items():
                                if not match_group(plugin['Group'], DEFAULT_FN_GROUPS): continue
                                if not plugin.get("AsButton", True): dropdown_fn_list.append(k)     # 排除已经是按钮的插件
                                elif plugin.get('AdvancedArgs', False): dropdown_fn_list.append(k)  # 对于需要高级参数的插件，亦在下拉菜单中显示
                            with gr.Row():
                                dropdown = gr.Dropdown(dropdown_fn_list, value=r"打开插件列表", label="", show_label=False).style(container=False)
                            with gr.Row():
                                plugin_advanced_arg = gr.Textbox(show_label=True, label="高级参数输入区", visible=False,
                                                                 placeholder="这里是特殊函数插件的高级参数输入区").style(container=False)
                            with gr.Row():
                                switchy_bt = gr.Button(r"请先从插件列表中选择", variant="secondary").style(size="sm")
                    with gr.Row():
                        with gr.Accordion("点击展开“文件下载区”。", open=False) as area_file_up:
                            file_upload = gr.Files(label="任何文件, 推荐上传压缩文件(zip, tar)", file_count="multiple", elem_id="elem_upload")

        with gr.Floating(init_x="0%", init_y="0%", visible=True, width=None, drag="forbidden", elem_id="tooltip"):
            with gr.Row():
                with gr.Tab("上传文件", elem_id="interact-panel"):
                    gr.Markdown("请上传本地文件/压缩包供“函数插件区”功能调用。请注意: 上传文件后会自动把输入区修改为相应路径。")
                    file_upload_2 = gr.Files(label="任何文件, 推荐上传压缩文件(zip, tar)", file_count="multiple", elem_id="elem_upload_float")

                with gr.Tab("更改模型和参数", elem_id="interact-panel"):
                    md_dropdown = gr.Dropdown(AVAIL_LLM_MODELS, value=LLM_MODEL, label="更换LLM模型/请求源").style(container=False)
                    _exist_model_config = cookies.value["llm_model_configs"][LLM_MODEL]
                    top_p = gr.Slider(minimum=-0, maximum=1.0, value=_exist_model_config["top_p"], step=0.01,interactive=True, label="Top-p (nucleus sampling)",)
                    temperature = gr.Slider(minimum=-0, maximum=2.0, value=_exist_model_config["temperature"], step=0.01, interactive=True, label="Temperature",)
                    max_length_sl = gr.Slider(minimum=256, maximum=1024*32, value=_exist_model_config["max_length_sl"], step=128, interactive=True, label="MaxLength",)
                    system_prompt = gr.Textbox(show_label=True, lines=2, placeholder=f"System Prompt", label="System prompt", value=_exist_model_config["system_prompt"])
                    # llm_config_msg = gr.Text(show_label=False, interactive=False, value="模型参数已保存", visible=False)
                    # btn_llm_config = gr.Button("设置模型参数", elem_id="btn_llm_config", variant="primary")

                with gr.Tab("界面外观", elem_id="interact-panel", render=is_show_all_function):
                    theme_dropdown = gr.Dropdown(AVAIL_THEMES, value=THEME, label="更换UI主题").style(container=False)
                    checkboxes = gr.CheckboxGroup(["基础功能区", "函数插件区", "浮动输入区", "输入清除键", "插件参数区"], value=["基础功能区", "函数插件区"], label="显示/隐藏功能区", elem_id='cbs').style(container=False)
                    opt = ["自定义菜单"]
                    value=[]
                    if ADD_WAIFU: opt += ["添加Live2D形象"]; value += ["添加Live2D形象"]
                    checkboxes_2 = gr.CheckboxGroup(opt, value=value, label="显示/隐藏自定义菜单", elem_id='cbsc').style(container=False)
                    dark_mode_btn = gr.Button("切换界面明暗 ☀", variant="secondary").style(size="sm")
                    dark_mode_btn.click(None, None, None, _js=js_code_for_toggle_darkmode)
                with gr.Tab("帮助", elem_id="interact-panel", render=is_show_all_function):
                    gr.Markdown(help_menu_description)

        with gr.Floating(init_x="20%", init_y="50%", visible=False, width="40%", drag="top") as area_input_secondary:
            with gr.Accordion("浮动输入区", open=True, elem_id="input-panel2"):
                with gr.Row() as row:
                    row.style(equal_height=True)
                    with gr.Column(scale=10):
                        txt2 = gr.Textbox(show_label=False, placeholder="Input question here.",
                                          elem_id='user_input_float', lines=8, label="输入区2").style(container=False)
                    with gr.Column(scale=1, min_width=40):
                        submitBtn2 = gr.Button("提交", variant="primary"); submitBtn2.style(size="sm")
                        resetBtn2 = gr.Button("重置", variant="secondary"); resetBtn2.style(size="sm")
                        stopBtn2 = gr.Button("停止", variant="secondary"); stopBtn2.style(size="sm")
                        clearBtn2 = gr.Button("清除", elem_id="elem_clear2", variant="secondary", visible=False); clearBtn2.style(size="sm")


        with gr.Floating(init_x="20%", init_y="50%", visible=False, width="40%", drag="top") as area_customize:
            with gr.Accordion("自定义菜单", open=True, elem_id="edit-panel"):
                with gr.Row() as row:
                    with gr.Column(scale=10):
                        AVAIL_BTN = [btn for btn in customize_btns.keys()] + [k for k in functional]
                        basic_btn_dropdown = gr.Dropdown(AVAIL_BTN, value="自定义按钮1", label="选择一个需要自定义基础功能区按钮").style(container=False)
                        basic_fn_title = gr.Textbox(show_label=False, placeholder="输入新按钮名称", lines=1).style(container=False)
                        basic_fn_prefix = gr.Textbox(show_label=False, placeholder="输入新提示前缀", lines=4).style(container=False)
                        basic_fn_suffix = gr.Textbox(show_label=False, placeholder="输入新提示后缀", lines=4).style(container=False)
                    with gr.Column(scale=1, min_width=70):
                        basic_fn_confirm = gr.Button("确认并保存", variant="primary"); basic_fn_confirm.style(size="sm")
                        basic_fn_clean   = gr.Button("恢复默认", variant="primary"); basic_fn_clean.style(size="sm")
                        def assign_btn(persistent_cookie_, cookies_, basic_btn_dropdown_, basic_fn_title, basic_fn_prefix, basic_fn_suffix, clean_up=False):
                            ret = {}
                            # 读取之前的自定义按钮
                            customize_fn_overwrite_ = cookies_['customize_fn_overwrite']
                            # 更新新的自定义按钮
                            customize_fn_overwrite_.update({
                                basic_btn_dropdown_:
                                    {
                                        "Title":basic_fn_title,
                                        "Prefix":basic_fn_prefix,
                                        "Suffix":basic_fn_suffix,
                                    }
                                }
                            )
                            if clean_up:
                                customize_fn_overwrite_ = {}
                            cookies_.update(customize_fn_overwrite_)    # 更新cookie
                            visible = (not clean_up) and (basic_fn_title != "")
                            if basic_btn_dropdown_ in customize_btns:
                                # 是自定义按钮，不是预定义按钮
                                ret.update({customize_btns[basic_btn_dropdown_]: gr.update(visible=visible, value=basic_fn_title)})
                            else:
                                # 是预定义按钮
                                ret.update({predefined_btns[basic_btn_dropdown_]: gr.update(visible=visible, value=basic_fn_title)})
                            ret.update({cookies: cookies_})
                            try: persistent_cookie_ = from_cookie_str(persistent_cookie_)   # persistent cookie to dict
                            except: persistent_cookie_ = {}
                            persistent_cookie_["custom_bnt"] = customize_fn_overwrite_      # dict update new value
                            persistent_cookie_ = to_cookie_str(persistent_cookie_)          # persistent cookie to dict
                            ret.update({py_pickle_cookie: persistent_cookie_})             # write persistent cookie
                            return ret

                        # update btn
                        h = basic_fn_confirm.click(assign_btn, [py_pickle_cookie, cookies, basic_btn_dropdown, basic_fn_title, basic_fn_prefix, basic_fn_suffix],
                                                   [py_pickle_cookie, cookies, *customize_btns.values(), *predefined_btns.values()])
                        h.then(None, [py_pickle_cookie], None, _js="""(py_pickle_cookie)=>{setCookie("py_pickle_cookie", py_pickle_cookie, 365);}""")
                        # clean up btn
                        h2 = basic_fn_clean.click(assign_btn, [py_pickle_cookie, cookies, basic_btn_dropdown, basic_fn_title, basic_fn_prefix, basic_fn_suffix, gr.State(True)],
                                                   [py_pickle_cookie, cookies, *customize_btns.values(), *predefined_btns.values()])
                        h2.then(None, [py_pickle_cookie], None, _js="""(py_pickle_cookie)=>{setCookie("py_pickle_cookie", py_pickle_cookie, 365);}""")

                        def persistent_cookie_reload(persistent_cookie_, cookies_):
                            ret = {}
                            for k in customize_btns:
                                ret.update({customize_btns[k]: gr.update(visible=False, value="")})

                            try: persistent_cookie_ = from_cookie_str(persistent_cookie_)    # persistent cookie to dict
                            except: return ret

                            customize_fn_overwrite_ = persistent_cookie_.get("custom_bnt", {})
                            cookies_['customize_fn_overwrite'] = customize_fn_overwrite_
                            ret.update({cookies: cookies_})

                            for k,v in persistent_cookie_["custom_bnt"].items():
                                if v['Title'] == "": continue
                                if k in customize_btns: ret.update({customize_btns[k]: gr.update(visible=True, value=v['Title'])})
                                else: ret.update({predefined_btns[k]: gr.update(visible=True, value=v['Title'])})
                            return ret

        # 功能区显示开关与功能区的互动
        def fn_area_visibility(a):
            ret = {}
            ret.update({area_input_primary: gr.update(visible=("浮动输入区" not in a))})
            ret.update({area_input_secondary: gr.update(visible=("浮动输入区" in a))})
            ret.update({plugin_advanced_arg: gr.update(visible=("插件参数区" in a))})
            if "浮动输入区" in a: ret.update({txt: gr.update(value="")})
            return ret
        checkboxes.select(fn_area_visibility, [checkboxes], [area_basic_fn, area_crazy_fn, area_input_primary, area_input_secondary, txt, txt2, plugin_advanced_arg] )
        checkboxes.select(None, [checkboxes], None, _js=js_code_show_or_hide)

        # 功能区显示开关与功能区的互动
        def fn_area_visibility_2(a):
            ret = {}
            ret.update({area_customize: gr.update(visible=("自定义菜单" in a))})
            return ret
        checkboxes_2.select(fn_area_visibility_2, [checkboxes_2], [area_customize] )
        checkboxes_2.select(None, [checkboxes_2], None, _js=js_code_show_or_hide_group2)

        # 整理反复出现的控件句柄组合
        input_combo = [cookies, max_length_sl, md_dropdown, txt, txt2, top_p, temperature, chatbot, history, system_prompt, plugin_advanced_arg]
        output_combo = [cookies, chatbot, history, status]
        predict_args = dict(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True)], outputs=output_combo)
        # 提交按钮、重置按钮
        cancel_handles.append(txt.submit(**predict_args))
        cancel_handles.append(txt2.submit(**predict_args))
        cancel_handles.append(submitBtn.click(**predict_args))
        cancel_handles.append(submitBtn2.click(**predict_args))
        resetBtn.click(None, None, [chatbot, history, status], _js=js_code_reset)   # 先在前端快速清除chatbot&status
        resetBtn2.click(None, None, [chatbot, history, status], _js=js_code_reset)  # 先在前端快速清除chatbot&status
        resetBtn.click(lambda: ([], [], "已重置"), None, [chatbot, history, status])    # 再在后端清除history
        resetBtn2.click(lambda: ([], [], "已重置"), None, [chatbot, history, status])   # 再在后端清除history
        clearBtn.click(None, None, [txt, txt2], _js=js_code_clear)
        clearBtn2.click(None, None, [txt, txt2], _js=js_code_clear)
        if AUTO_CLEAR_TXT:
            submitBtn.click(None, None, [txt, txt2], _js=js_code_clear)
            submitBtn2.click(None, None, [txt, txt2], _js=js_code_clear)
            txt.submit(None, None, [txt, txt2], _js=js_code_clear)
            txt2.submit(None, None, [txt, txt2], _js=js_code_clear)
        # 基础功能区的回调函数注册
        for k in functional:
            if ("Visible" in functional[k]) and (not functional[k]["Visible"]): continue
            click_handle = functional[k]["Button"].click(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True), gr.State(k)], outputs=output_combo)
            cancel_handles.append(click_handle)
        for btn in customize_btns.values():
            click_handle = btn.click(fn=ArgsGeneralWrapper(predict), inputs=[*input_combo, gr.State(True), gr.State(btn.value)], outputs=output_combo)
            cancel_handles.append(click_handle)
        # 文件上传区，接收文件后与chatbot的互动
        file_upload.upload(on_file_uploaded, [file_upload, chatbot, txt, txt2, checkboxes, cookies], [chatbot, txt, txt2, cookies]).then(None, None, None,   _js=r"()=>{toast_push('上传完毕 ...'); cancel_loading_status();}")
        if file_upload_2:
            file_upload_2.upload(on_file_uploaded, [file_upload_2, chatbot, txt, txt2, checkboxes, cookies], [chatbot, txt, txt2, cookies]).then(None, None, None, _js=r"()=>{toast_push('上传完毕 ...'); cancel_loading_status();}")
        # 函数插件-固定按钮区
        for k in plugins:
            if not plugins[k].get("AsButton", True): continue
            click_handle = plugins[k]["Button"].click(ArgsGeneralWrapper(plugins[k]["Function"]), [*input_combo], output_combo)
            click_handle.then(on_report_generated, [cookies, file_upload, chatbot], [cookies, file_upload, chatbot])
            cancel_handles.append(click_handle)
        # 函数插件-下拉菜单与随变按钮的互动
        def on_dropdown_changed(k):
            variant = plugins[k]["Color"] if "Color" in plugins[k] else "secondary"
            info = plugins[k].get("Info", k)
            ret = {switchy_bt: gr.update(value=k, variant=variant, info_str=f'函数插件区: {info}')}
            if plugins[k].get("AdvancedArgs", False): # 是否唤起高级插件参数区
                ret.update({plugin_advanced_arg: gr.update(visible=True,  label=f"插件[{k}]的高级参数说明：" + plugins[k].get("ArgsReminder", [f"没有提供高级参数功能说明"]))})
            else:
                ret.update({plugin_advanced_arg: gr.update(visible=False, label=f"插件[{k}]不需要高级参数。")})
            return ret
        dropdown.select(on_dropdown_changed, [dropdown], [switchy_bt, plugin_advanced_arg] )

        def on_md_dropdown_changed(cookies_, k):
            model_config = cookies_["llm_model_configs"][k]
            # return _llm_model_configs_cookies, _top_p, _temperature, _max_tokens, _system_prompt
            return cookies_, gr.update(label="当前模型："+k), model_config["top_p"], model_config["temperature"], model_config["max_length_sl"], model_config["system_prompt"], None, [], None

        md_dropdown.select(on_md_dropdown_changed,
                           [cookies, md_dropdown],
                           [cookies, chatbot, top_p, temperature, max_length_sl, system_prompt, chatbot, history, status])

        from functools import partial
        def on_llm_config_change(keyname, cookies_, model_name_, val):
            model_config = cookies_["llm_model_configs"][model_name_]
            model_config.update({
                keyname: val
            })
            return cookies_

        top_p.change(partial(on_llm_config_change, "top_p"), [cookies, md_dropdown, top_p], [cookies])
        temperature.change(partial(on_llm_config_change, "temperature"), [cookies, md_dropdown, temperature], [cookies])
        max_length_sl.change(partial(on_llm_config_change, "max_length_sl"), [cookies, md_dropdown, max_length_sl], [cookies])
        system_prompt.change(partial(on_llm_config_change, "system_prompt"), [cookies, md_dropdown, system_prompt], [cookies])

        def on_theme_dropdown_changed(theme, secret_css):
            adjust_theme, css_part1, _, adjust_dynamic_theme = load_dynamic_theme(theme)
            if adjust_dynamic_theme:
                css_part2 = adjust_dynamic_theme._get_theme_css()
            else:
                css_part2 = adjust_theme()._get_theme_css()
            return css_part2 + css_part1

        theme_handle = theme_dropdown.select(on_theme_dropdown_changed, [theme_dropdown, secret_css], [secret_css])
        theme_handle.then(
            None,
            [secret_css],
            None,
            _js=js_code_for_css_changing
        )
        # 随变按钮的回调函数注册
        def route(request: gr.Request, k, *args, **kwargs):
            if k in [r"打开插件列表", r"请先从插件列表中选择"]: return
            yield from ArgsGeneralWrapper(plugins[k]["Function"])(request, *args, **kwargs)
        click_handle = switchy_bt.click(route,[switchy_bt, *input_combo], output_combo)
        click_handle.then(on_report_generated, [cookies, file_upload, chatbot], [cookies, file_upload, chatbot])
        cancel_handles.append(click_handle)
        # 终止按钮的回调函数注册
        stopBtn.click(fn=None, inputs=None, outputs=None, cancels=cancel_handles)
        stopBtn2.click(fn=None, inputs=None, outputs=None, cancels=cancel_handles)
        plugins_as_btn = {name:plugin for name, plugin in plugins.items() if plugin.get('Button', None)}
        def on_group_change(group_list):
            btn_list = []
            fns_list = []
            if not group_list: # 处理特殊情况：没有选择任何插件组
                return [*[plugin['Button'].update(visible=False) for _, plugin in plugins_as_btn.items()], gr.Dropdown.update(choices=[])]
            for k, plugin in plugins.items():
                if plugin.get("AsButton", True):
                    btn_list.append(plugin['Button'].update(visible=match_group(plugin['Group'], group_list))) # 刷新按钮
                    if plugin.get('AdvancedArgs', False): dropdown_fn_list.append(k) # 对于需要高级参数的插件，亦在下拉菜单中显示
                elif match_group(plugin['Group'], group_list): fns_list.append(k) # 刷新下拉列表
            return [*btn_list, gr.Dropdown.update(choices=fns_list)]
        plugin_group_sel.select(fn=on_group_change, inputs=[plugin_group_sel], outputs=[*[plugin['Button'] for name, plugin in plugins_as_btn.items()], dropdown])
        if ENABLE_AUDIO:
            from crazy_functions.live_audio.audio_io import RealtimeAudioDistribution
            rad = RealtimeAudioDistribution()
            def deal_audio(audio, cookies):
                rad.feed(cookies['uuid'].hex, audio)
            audio_mic.stream(deal_audio, inputs=[audio_mic, cookies])


        demo.load(init_cookie, inputs=[cookies], outputs=[cookies])
        demo.load(persistent_cookie_reload, inputs = [py_pickle_cookie, cookies],
            outputs = [py_pickle_cookie, cookies, *customize_btns.values(), *predefined_btns.values()], _js=js_code_for_persistent_cookie_init)
        demo.load(None, inputs=[dark_mode], outputs=None, _js="""(dark_mode)=>{apply_cookie_for_checkbox(dark_mode);}""")    # 配置暗色主题或亮色主题
        demo.load(None, inputs=[gr.Textbox(LAYOUT, visible=False)], outputs=None, _js='(LAYOUT)=>{GptAcademicJavaScriptInit(LAYOUT);}')

    # gradio的inbrowser触发不太稳定，回滚代码到原始的浏览器打开函数
    def run_delayed_tasks():
        import threading, webbrowser, time
        print(f"如果浏览器没有自动打开，请复制并转到以下URL：")
        if DARK_MODE:   print(f"\t「暗色主题已启用（支持动态切换主题）」: http://localhost:{PORT}")
        else:           print(f"\t「亮色主题已启用（支持动态切换主题）」: http://localhost:{PORT}")

        def auto_updates(): time.sleep(0); auto_update()
        def open_browser(): time.sleep(2); webbrowser.open_new_tab(f"http://localhost:{PORT}")
        def warm_up_mods(): time.sleep(6); warm_up_modules()

        threading.Thread(target=auto_updates, name="self-upgrade", daemon=True).start() # 查看自动更新
        threading.Thread(target=open_browser, name="open-browser", daemon=True).start() # 打开浏览器页面
        threading.Thread(target=warm_up_mods, name="warm-up", daemon=True).start()      # 预热tiktoken模块

    run_delayed_tasks()
    demo.queue(concurrency_count=CONCURRENT_COUNT, status_update_rate="auto").launch(
        quiet=True,
        server_name="0.0.0.0",
        ssl_keyfile=None if SSL_KEYFILE == "" else SSL_KEYFILE,
        ssl_certfile=None if SSL_CERTFILE == "" else SSL_CERTFILE,
        ssl_verify=False,
        server_port=PORT,
        favicon_path=os.path.join(Path.cwd(), "docs/logo.png"),
        auth=AUTHENTICATION if len(AUTHENTICATION) != 0 else None,
        blocked_paths=["config.py","config_private.py","docker-compose.yml","Dockerfile",f"{PATH_LOGGING}/admin"])

    # 如果需要在二级路径下运行
    # CUSTOM_PATH = get_conf('CUSTOM_PATH')
    # if CUSTOM_PATH != "/":
    #     from toolbox import run_gradio_in_subpath
    #     run_gradio_in_subpath(demo, auth=AUTHENTICATION, port=PORT, custom_path=CUSTOM_PATH)
    # else:
    #     demo.launch(server_name="0.0.0.0", server_port=PORT, auth=AUTHENTICATION, favicon_path="docs/logo.png",
    #                 blocked_paths=["config.py","config_private.py","docker-compose.yml","Dockerfile",f"{PATH_LOGGING}/admin"])

if __name__ == "__main__":
    main()