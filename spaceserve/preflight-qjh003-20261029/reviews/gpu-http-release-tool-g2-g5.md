结论：REQUEST_CHANGES（工具窄G2；发布G5尚未通过）
BLOCKING：1
reviewed_at_utc：2026-10-29T00:32:42Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

仅只读本地三个候选工具、旧已审同类脚本及真实helper源码依赖，没有执行工具、测试、网络或credential helper。依明确请求保存本审查原文，不改代码。

BLOCKING：

1. outputs/migration-qjh003/publish_space_release.py:14，helper导入路径少上一层。该脚本的Path(__file__).resolve().parents[1]为项目outputs目录，当前实际拼出outputs/work/repository-upload；github_api.py、upload_buffered_asset.py及其release_assets.py依赖实际位于项目work/repository-upload。标准直接执行会无法导入，curl draft verifier也继承此问题。最小修复为parents[2]/'work/repository-upload'，或先计算真实项目ROOT再拼路径；不依赖外部PYTHONPATH碰巧补齐。

其余核验：
- 仅当前新tag和tar/source-files两资产；repo/public状态、G5 passed/scope/tag/status、完整commit、资产bytes/SHA、draft上传、下载验证后publish的既有强校验保留。
- 旧四Release ID明确排除，不能以state改写旧Release；旧13资产前后API快照核验仍是主流程的实际必做事项，工具本身没有替代该核验。
- 真实github_api函数通过Git credential helper只在调用时内存取凭据；helper导入本身无网络。buffered connection仅允许uploads.github.com；其导入release_assets.py没有触发main发布流程。
- curl draft verifier的认证与签名URL通过stdin而非argv传递，跨CDN不携Authorization，HTTPS/目标host检查保持；public verifier匿名GET并核实际bytes/SHA，结果不能用API digest替代。
- 发布正文正确限定313预检、formal0/54、五条非逐token相等及decoder互斥未证；没有新性能/完整项目完成声明。

NON-BLOCKING：
1. publish_space_release.py:98发布body仍写“证据ZIP”，实际资产是tar.gz；改为“证据归档”即可，避免格式误导。

QUESTIONS：无。

修复后仅需针对同范围窄复审。数据commit尚未创建，本审查不能提前批准具体commit发布：正式G5仍须绑定精确数据commit、tar355691974B/SHA799d1774f1e45a82dfdf9c516c7f757c5911d6e4cf8e769ccf5e172815edeb88及source-files.json实际SHA；其后按真实draft下载、公开下载与旧Release/资产不变证据闭环。

GATE_RESULT: {"gate":"G2+G5-tool-scope","decision":"REQUEST_CHANGES","blocking":1,"exact_data_commit_publication_approved":false}

## B1窄复审

结论：APPROVE（工具代码范围）
BLOCKING：0
reviewed_at_utc：2026-10-29T00:35:23Z

已只读确认第14行改为parents[2]/'work/repository-upload'，实际解析至本项目work/repository-upload；github_api.py、upload_buffered_asset.py、release_assets.py均存在。WORK仍为实际发布材料所在migration目录。B1关闭，不重复全审；未运行编译、工具、网络或credential helper。

此批准仅关闭工具路径阻塞，不能替代待创建精确数据commit及两资产SHA绑定的正式发布G5。原初审与发布正文格式nit保留。

GATE_RESULT: {"gate":"G2-release-tools-recheck","decision":"APPROVE","blocking":0,"exact_data_commit_publication_approved":false}

## 精确Release发布G5

结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T00:36:15Z

已只读核验精确data commit2f3cf04df1299039c791ec42473b0758fa606b4e，tree40bbd1a2b6f93f298ea94d1de0c8ae8efc9cb420。approval candidate SHA为baaa8dbc82fa9d131a6258801ac0476310d8c007901f2cd8b0cd7c97730ab0fe，其repo/tag/status/commit及两资产与assets-for-upload.json一致。

- space-http-20261029-raw.tar.gz实际355691974B，重算SHA799d1774f1e45a82dfdf9c516c7f757c5911d6e4cf8e769ccf5e172815edeb88。
- source-files.json实际108097B，重算SHA12d1fe2dacb90101fa98ec899de5ad6006c9b36592ec37da8d9416aa80e36c74；与精确data commit的spaceserve/preflight-qjh003-20261029/source-files.json Git blob原字节完全一致。

允许将上述精确candidate作为真实G5批准文件使用，仅创建唯一新tag spaceserve-qjh003-preflight-2026-10-29的draft Release并上传两件原字节资产。必须实际draft下载bytes/SHA通过后才publish，再匿名公开下载核验；旧四Release/13资产身份、size/digest/URL及tag前后核验保持不变。已有tag/Release或不同资产不得覆盖。

本结论只批准精确发布操作，不宣称已远端创建、上传或下载成功；本轮未执行网络。数据与运行producer版本分别保留，正式0/54，无新增完整性能成绩、decoder完整分区或项目整体完成结论。

GATE_RESULT: {"gate":"G5-release-publication","commit":"2f3cf04df1299039c791ec42473b0758fa606b4e","tree":"40bbd1a2b6f93f298ea94d1de0c8ae8efc9cb420","tag":"spaceserve-qjh003-preflight-2026-10-29","approval_candidate_sha256":"baaa8dbc82fa9d131a6258801ac0476310d8c007901f2cd8b0cd7c97730ab0fe","decision":"APPROVE","blocking":0}

## Native TLS传输窄复审

结论：APPROVE（G2及原精确发布G5的传输补充）
BLOCKING：0
reviewed_at_utc：2026-10-29T00:39:19Z

已只读检查github_native_transport.py及所复用的publisher/verifiers/helper依赖，没有执行网络、工具或credential helper。允许仅以native curl替换同一精确发布流程的TLS传输；data commit、tag、两资产bytes/SHA及旧四Release/13资产保护不变。

- API仅固定仓库HTTPS，curl禁配置、禁redirect、零自动重试并有连接/总时限；认证仅stdin，不进入argv或日志。失败响应不打印。
- create/publish/verify仍调用原publisher及下载校验guard；native upload重新核G5范围、repo、新draft/tag/commit/旧Release排除、本地资产SHA与实际asset digest，不覆盖异字节资产。
- upload失败后必须先查当前assets再续接；不能将TLS异常等同未上传。draft bytes/SHA真实下载通过后才publish，随后匿名公开下载及旧四Release/13资产前后快照核验仍必做。

本次POST结果未知，执行顺序必须先用新只读inspect查询当前Release/tag及精确ref，保存原始响应。只有确认本tag的Release和ref均不存在才可create。若已存在符合本次commit/tag的唯一draft，应读取详情并将其真实身份作为恢复state记录，沿同draft继续；不能再create。若已published、重复、身份不符或查询仍失败，停止并保留未知状态，不猜测、不反复POST。状态恢复不得改写首次TLS失败记录。

inspect只输出当前列表，不自动证明tag不存在；主线程必须实际完成上述结果核验。当前脚本未在本审查中执行，不能声称已创建或上传成功。

NON-BLOCKING：无新增项。QUESTIONS：无。

GATE_RESULT: {"gate":"G2+G5-native-transport-addendum","commit":"2f3cf04df1299039c791ec42473b0758fa606b4e","tag":"spaceserve-qjh003-preflight-2026-10-29","decision":"APPROVE","blocking":0,"requires_actual_inspection_before_create":true}

## Draft body措辞窄G5

结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T00:44:34Z

已只读审查release-body.md及当前draft/download-verified本地原件。body正确将资产描述为本次完整run的tar.gz和逐文件SHA，前序失败与可读报告另在Git页面；披露五条输出token差异、既定语义契约、formal0/54、无性能比值及decoder互斥未证明，没有将失败误称包含在成功tar内。

允许仅PATCH已核draft427341677的body为该文件原文，随后继续原publisher publish流程。tag spaceserve-qjh003-preflight-2026-10-29、data commit2f3cf04df1299039c791ec42473b0758fa606b4e、两asset ID686855009/686857249及既定bytes/SHA保持不变；PATCH后重读身份与body，再由原publish校验下载proof/current assets后发布。

download-verified原件记录精确两资产SHA通过；本审查没有重新联网下载。draft当前untagged browser URL不作为最终公开验收URL，publish后仍须用正式tag匿名下载核bytes/SHA，并完成旧四Release/13资产身份等前后核验。

本轮仅文本范围G5，不宣称已PATCH或发布，不授权改tag、commit、资产内容或旧Release。

GATE_RESULT: {"gate":"G5-release-body-only","release_id":427341677,"commit":"2f3cf04df1299039c791ec42473b0758fa606b4e","decision":"APPROVE","blocking":0}

## Draft临时tag身份恢复窄G5

结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T00:47:03Z

已只读核release-publish-refusal.json：同一draft427341677实际为untagged-23ecabff87691eabf67c，commit仍正确，原publish guard拒绝是正确行为。现有证据只证明观察到该tag差异，不独立证明GitHub partial PATCH自动变化的因果。

允许先实际只读确认预期tag ref不存在、没有其他Release引用预期tag；结果不明确或已有冲突则停止。随后仅对同一新draft427341677作一次完整身份PATCH：已审body、tag_name=spaceserve-qjh003-preflight-2026-10-29、target_commitish=2f3cf04df1299039c791ec42473b0758fa606b4e、draft=true。不得删除、移动或重指任何已存在tag，不修改旧四Release。

PATCH后回读并保存实际完整Release身份、body、两asset ID/size/digest/URL及tag refs，与本次精确批准比较；全部一致才将真实响应保存state并继续未放宽的原publish流程。若PATCH响应丢失先inspect实际状态，不盲目重复写。已下载proof与资产内容保持，公开后仍须正式tag匿名下载和旧四/13前后核验。

旧拒绝、临时tag状态及操作顺序原件保留，不能将首次publish拒绝重标成功。此批准不是允许从本地state推断远端身份；本审查未联网或操作Release。

GATE_RESULT: {"gate":"G5-draft-identity-recovery","release_id":427341677,"tag":"spaceserve-qjh003-preflight-2026-10-29","commit":"2f3cf04df1299039c791ec42473b0758fa606b4e","decision":"APPROVE","blocking":0,"requires_actual_conflict_free_ref_inspection":true}

## Publish完整身份PATCH两行窄复审

结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T00:48:47Z

已只读确认publisher:158–159仅将最终publish PATCH显式带上draft=false、tag_name=TAG、target_commitish=approved_commit，并assert响应非draft且tag/commit精确一致。原下载proof、当前资产身份/digest、Release旧ID排除及ref校验仍保留。

release-recovery-after.json记录同一427341677为正确预期tag、正确2f3cf04 commit、draft=true。允许按上述完整身份PATCH继续原精确发布范围；不扩大资产、tag或commit范围，不把之前tag变化未知原因写成平台机制定论。此次未联网或发布，成功仍须实际响应及匿名下载/旧四13核验。

GATE_RESULT: {"gate":"G5-publish-explicit-identity-two-line-recheck","release_id":427341677,"commit":"2f3cf04df1299039c791ec42473b0758fa606b4e","decision":"APPROVE","blocking":0}

## 匿名public API→CDN下载只读工具窄G2/G5

结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-29T00:56:58Z

已只读检查verify_space_public_api.py。匿名资产API请求删除Authorization，代码未调用publisher.token或publisher.api；publisher及helper的导入本身不会取凭据或发网络请求。API和CDN两段curl均禁默认配置、HTTPS、无自动重试/redirect跟随，API只接受302及精确release-assets.githubusercontent.com HTTPS Location。signed URL只通过stdin传递，不写argv、日志或proof。

main绑定已公开427341677、非draft、预期tag及approval commit/assets，下载后逐项核实际bytes/SHA，只有两资产全部完成才排他写public-api-download-verified.json。此操作仅GET及本地proof写入，不修改Release/tag/assets或旧四/13。

允许执行此同范围匿名完整下载验证。结果只能称anonymous public asset API→HTTPS CDN链路实际bytes/SHA通过；不能写成browser_download_url链路成功。proof中的public_browser_url仅是元数据标识，不是已验证的访问路径。原browser/IPv4连接超时原件保留，不替换或覆盖public-download-verified证明。

本轮没有联网下载，不能提前声称匿名验收成功。顶层docstring仍写draft为继承措辞，不影响实际published身份guard，建议下次文档收口修正。

GATE_RESULT: {"gate":"G2+G5-anonymous-public-API-verification","release_id":427341677,"scope":"readonly_anonymous_public_asset_API_to_CDN_actual_bytes_SHA_only","decision":"APPROVE","blocking":0,"browser_download_path_proven":false}
