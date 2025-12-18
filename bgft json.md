the BGFT module doesnt seem to take in a plain PKG file, instead it takes in a JSON file like this:

```json
{
  "originalFileSize": 40649097216,
  "packageDigest": "788BB54D8478C1C41D3426E2136698E7DF36D55391AC04B8F27A2F623637B315",
  "numberOfSplitFiles": 1,
  "pieces": [
    {
      "url": "http://my.domain/example.pkg",
      "fileOffset": 0,
      "fileSize": 40649097216,
      "hashValue": "0000000000000000000000000000000000000000"
    }
  ]
}
```

the `packageDigest` is taken from the PKG's digest field.
the `hashValue` in pieces can seemingly be all zeroes

BGFT then gets a task with a call like this:
```c
SceBgftDownloadParam params;
SceBgftTaskId task_id = SCE_BGFT_INVALID_TASK_ID;
int ret;

params.entitlementType = 5; /* TODO: figure out */
params.userId = userId /* sceUserServiceGetForegroundUser */;
params.id = content_id /* param.sfo CONTENT_ID */;
params.contentUrl = content_url /* path to the above JSON */;
params.contentName = content_name /* title of the app */;
params.iconPath = icon_path /* path to the app icon on the local filesystem, or "" */;
params.playgoScenarioId = "0";
params.option = SCE_BGFT_TASK_OPT_DISABLE_CDN_QUERY_PARAM;
params.packageType = package_type /* one of: PS4GD, PS4AC, PS4AL, PS4DP */;
params.packageSubType = "";
params.packageSize = package_size /* size of the pkg file (also in the JSON) */;
if (!isPatch) {
  ret = sceBgftDownloadRegisterTask(&params, &task_id);
} else {
  ret = sceBgftDebugDownloadRegisterPkg(&params, &task_id);
}
```
