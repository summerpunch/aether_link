{
    "workflow_id": "c2208154-b2e7-45a8-8978-9f24b58e9222",
    "nodes": [
        {
            "id": "d7870622-ae26-4a7c-aca7-c4d1912fdd82",
            "node_type": "start",
            "position": {
                "x": 173.2275347970047,
                "y": 125.52719912826424
            },
            "description": "工作流的起点节点，支持定义工作流的起点输入等信息",
            "inputs": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "工作流的起点节点，支持定义工作流的起点输入等信息。",
                    "required": true
                },
                {
                    "name": "location",
                    "type": "string",
                    "description": "需要查询的城市地址信息",
                    "required": true
                }
            ],
            "title": "开始节点_dnVLX"
        },
        {
            "id": "66dd3c90-82d2-4268-82da-38c13233d548",
            "node_type": "end",
            "position": {
                "x": 1386.238702373132,
                "y": 352.31300555332837
            },
            "description": "工作流的结束节点，支持定义工作流最终输出的变量等信息",
            "outputs": [
                {
                    "name": "output",
                    "description": "",
                    "required": true,
                    "type": "string",
                    "value": {
                        "type": "ref",
                        "content": {
                            "ref_node_id": "351862b6-6a8d-4f0e-9f2e-709cbd2b148d",
                            "ref_var_name": "output"
                        }
                    },
                    "meta": {}
                }
            ],
            "title": "结束节点_Z1LoP"
        },
        {
            "id": "351862b6-6a8d-4f0e-9f2e-709cbd2b148d",
            "node_type": "llm",
            "position": {
                "x": 956.3022321174426,
                "y": 80.79850813269988
            },
            "title": "大语言模型_zSE8t",
            "description": "调用大语言模型，根据输入参数和提示词生成回复。",
            "prompt": "你是一个强有力的AI机器人，请根据用户的提问回复特定的内容，用户的提问是: {{query}}。",
            "language_model_config": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "parameters": {
                    "frequency_penalty": 0.2,
                    "max_tokens": 8192,
                    "presence_penalty": 0.2,
                    "temperature": 0.5,
                    "top_p": 0.85
                }
            },
            "inputs": [
                {
                    "name": "query",
                    "description": "",
                    "required": true,
                    "type": "string",
                    "value": {
                        "type": "ref",
                        "content": {
                            "ref_node_id": "e96b3e1a-0d64-413a-9c21-dd3aa9e97194",
                            "ref_var_name": "text"
                        }
                    },
                    "meta": {}
                }
            ],
            "outputs": [
                {
                    "name": "output",
                    "type": "string",
                    "value": {
                        "type": "generated",
                        "content": ""
                    }
                }
            ],
            "model_config": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "parameters": {
                    "frequency_penalty": 0.2,
                    "max_tokens": 8192,
                    "presence_penalty": 0.2,
                    "temperature": 0.5,
                    "top_p": 0.85
                }
            }
        },
        {
            "id": "e96b3e1a-0d64-413a-9c21-dd3aa9e97194",
            "node_type": "tool",
            "position": {
                "x": 499.94574216685317,
                "y": 129.55266634686302
            },
            "title": "扩展插件_TyOvm",
            "description": "调用插件广场或自定义API插件，支持能力扩展和复用",
            "tool_type": "builtin_tool",
            "provider_id": "time",
            "tool_id": "current_time",
            "params": {},
            "inputs": [],
            "outputs": [
                {
                    "name": "text",
                    "type": "string",
                    "value": {
                        "type": "generated",
                        "content": ""
                    }
                }
            ],
            "meta": {
                "type": "builtin_tool",
                "provider": {
                    "id": "time",
                    "name": "time",
                    "label": "时间",
                    "icon": "/api/builtin-tools/time/icon",
                    "description": "一个用于获取当前时间的工具"
                },
                "tool": {
                    "id": "current_time",
                    "name": "current_time",
                    "label": "获取当前时间",
                    "description": "一个用于获取当前时间的工具。",
                    "params": {}
                }
            }
        }
    ],
    "edges": [
        {
            "id": "f00f0b00-b133-4cca-ab77-b47dc0df78a4",
            "source": "351862b6-6a8d-4f0e-9f2e-709cbd2b148d",
            "source_type": "llm",
            "source_handle_id": null,
            "target": "66dd3c90-82d2-4268-82da-38c13233d548",
            "target_type": "end"
        },
        {
            "id": "1e1f1783-7bd8-48e2-baab-467af4eaa10a",
            "source": "e96b3e1a-0d64-413a-9c21-dd3aa9e97194",
            "source_type": "tool",
            "source_handle_id": null,
            "target": "351862b6-6a8d-4f0e-9f2e-709cbd2b148d",
            "target_type": "llm"
        },
        {
            "id": "4a95ec4a-4dce-466e-9e8a-181c62dff5d8",
            "source": "d7870622-ae26-4a7c-aca7-c4d1912fdd82",
            "source_type": "start",
            "source_handle_id": null,
            "target": "e96b3e1a-0d64-413a-9c21-dd3aa9e97194",
            "target_type": "tool"
        }
    ]
}