post url
header:
Govee-API-Key :Govee-API-Key
Content-Type ： application/json

boddy
{
    "requestId": "uuid",
    "payload": {
        "sku": "H7172",
        "device": "2E:78:D0:C9:07:8D:78:A0",
        "capability": {
            "type": "devices.capabilities.on_off",
            "instance": "powerSwitch",
            "value": 0
        }
    }
}
result

{
    "requestId": "uuid",
    "msg": "success",
    "code": 200,
    "capability": {
        "type": "devices.capabilities.on_off",
        "instance": "powerSwitch",
        "state": {
            "status": "success"
        },
        "value": 0
    }
}

