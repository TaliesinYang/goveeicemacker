
GET /router/api/v1/user/devices HTTP/1.1
Host: https://openapi.api.govee.com
Content-Type: application/json
Govee-API-Key: xxxx



result


{
    "code": 200,
    "message": "success",
    "data": [
        {
            "sku": "H7172",
            "device": "2E:78:D0:C9:07:8D:78:A0",
            "deviceName": "Smart Ice Maker",
            "type": "devices.types.ice_maker",
            "capabilities": [
                {
                    "type": "devices.capabilities.on_off",
                    "instance": "powerSwitch",
                    "parameters": {
                        "dataType": "ENUM",
                        "options": [
                            {
                                "name": "on",
                                "value": 1
                            },
                            {
                                "name": "off",
                                "value": 0
                            }
                        ]
                    }
                },
                {
                    "type": "devices.capabilities.work_mode",
                    "instance": "workMode",
                    "parameters": {
                        "dataType": "STRUCT",
                        "fields": [
                            {
                                "fieldName": "workMode",
                                "dataType": "ENUM",
                                "options": [
                                    {
                                        "name": "LargeIce",
                                        "value": 1
                                    },
                                    {
                                        "name": "MediumIce",
                                        "value": 2
                                    },
                                    {
                                        "name": "SmallIce",
                                        "value": 3
                                    }
                                ],
                                "required": true
                            },
                            {
                                "fieldName": "modeValue",
                                "dataType": "ENUM",
                                "options": [
                                    {
                                        "defaultValue": 0,
                                        "name": "LargeIce"
                                    },
                                    {
                                        "defaultValue": 0,
                                        "name": "MediumIce"
                                    },
                                    {
                                        "defaultValue": 0,
                                        "name": "SmallIce"
                                    }
                                ],
                                "required": false
                            }
                        ]
                    }
                },
                {
                    "type": "devices.capabilities.event",
                    "instance": "lackWaterEvent",
                    "alarmType": 51,
                    "eventState": {
                        "options": [
                            {
                                "name": "lack",
                                "value": 1,
                                "message": "Lack of Water"
                            }
                        ]
                    }
                },
                {
                    "type": "devices.capabilities.event",
                    "instance": "iceFull",
                    "alarmType": 58,
                    "eventState": {
                        "options": [
                            {
                                "name": "iceFull",
                                "value": 1,
                                "message": "ice maker full"
                            }
                        ]
                    }
                }
            ]
        }
    ]
}