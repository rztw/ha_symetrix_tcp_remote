## [English Version]

## Symetrix DSP Home Assistant Integration (`symetrix_ha`)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/U7U21VQTGJ)

This is a Home Assistant custom integration that controls Symetrix DSP over **TCP**, with best-effort **bi-directional synchronization**:

- Send commands from HA (for example, `CS 101 <value>`, `LP 1`).
- Update HA entity states from Symetrix push messages (for example, `#00101=56173`).

This integration focuses on TCP control and state sync between Home Assistant and Symetrix DSP.

---

### 1. File Structure Overview

- `manifest.json`
  - Integration manifest, with domain set to `symetrix_ha`.
  - Declares platforms: `button`, `number`, `binary_sensor`, `sensor`, `switch`.
- `__init__.py`
  - Implements the core `SymetrixClient` (persistent TCP client):
    - Connects to Symetrix DSP over TCP.
    - Sends `GPR` / `GPU` on startup to retrieve latest preset and push-enabled control list.
    - Continuously reads TCP data ending with `\r`, and parses:
      - Push updates: `#00101=56173` (Control 101 value).
      - GS responses: `{GS 101} 32768`, etc.
    - Uses callbacks to propagate control value changes and connection status to HA entities.
  - `async_setup_entry`:
    - Reads `host` / `port` from config flow.
    - Loads controls from `symetrix_controls.yaml` into `hass.data[DOMAIN][entry_id]["controls"]`.
    - Starts `SymetrixClient` and forwards supported platforms.
- `config_flow.py`
  - UI flow for setup: only `host` and `port` are required.
  - After setup, controls are managed by `symetrix_controls.yaml` (no YAML paste in UI needed).
- `symetrix_controls.yaml`
  - **The control list file you should edit**.
  - Loaded at startup to dynamically create slider (`number`) and toggle (`switch`) entities.
- `button.py`
  - Creates:
    - `Flash DSP` -> `FU 4`
    - `Reboot DSP` -> `R!`
    - `Reconnect` -> force reconnect (`SymetrixClient.reconnect()`).
- `switch.py`
  - Dynamically creates `switch` entities from `type: switch` entries.
  - Auto-syncs state based on push / GS messages.
- `number.py`
  - Dynamically creates `number` entities from `type: number` entries.
  - Supports:
    - `scale: db_72_12`: maps `0~65535` to `-72~+12 dB` and back, then sends `CS`.
    - `scale: raw`: uses 0~65535 directly.
- `binary_sensor.py`
  - `Connection` entity shows connectivity to Symetrix.
- `sensor.py`
  - `Last TCP message` shows the latest raw TCP line received from Symetrix.
  - Disabled by default; enable only for troubleshooting.
- `services.yaml`
  - Defines service calls for automation/scripts, such as:
    - `symetrix_ha.send_raw`
    - `symetrix_ha.load_preset`
    - `symetrix_ha.flash`
    - `symetrix_ha.set_value`
    - `symetrix_ha.change_value`
    - `symetrix_ha.get_latest_preset`

---

### 2. Installation

#### Option A: Install via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OWNER&repository=REPO&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=symetrix_ha)

Replace `OWNER` / `REPO` in the HACS link with your actual GitHub repository.

1. In HACS, go to **Integrations** -> menu -> **Custom repositories**.
2. Add this GitHub repository URL, set category to **Integration**.
3. Search and install **Symetrix DSP TCP**.
4. Restart Home Assistant.
5. Go to **Settings -> Devices & Services -> Add Integration**, then add **Symetrix DSP TCP** and enter `host` / `port`.

#### Option B: Manual install

1. Copy `custom_components/symetrix_ha` from this repo to:
   - `/config/custom_components/symetrix_ha`
2. Restart Home Assistant.
3. Go to **Settings -> Devices & Services -> Add Integration**, then add **Symetrix DSP TCP** and enter `host` / `port`.

#### Control list file

- Edit `symetrix_controls.yaml` under `custom_components/symetrix_ha/`.
- After changing controls, restart Home Assistant to regenerate entities.

---

### 3. TCP Command Mapping

All commands are automatically sent with `\r\n` suffix.

- `symetrix_ha.send_raw` -> raw `command` string
- `symetrix_ha.load_preset` -> `LP <preset>`
- `symetrix_ha.load_global_preset` -> `LPG <preset>`
- `symetrix_ha.flash` -> `FU <amount>`
- `symetrix_ha.reboot` -> `R!`
- `symetrix_ha.set_value` -> `CS <control> <value>`
- `symetrix_ha.change_value` -> `CC <control> <1/0> <step>`
- `symetrix_ha.get_latest_preset` -> `GPR`

---

### 4. `symetrix_controls.yaml` Example: Sample Fader / Sample Mute

Each item defines one `number` or `switch` entity:

```yaml
# EXAMPLE: Output fader: Control 101, mapped to -72 ~ +12 dB
- control: 101
  type: number
  name: Sample Fader
  scale: db_72_12
  min: -72
  max: 12
  step: 0.5

# EXAMPLE: Output mute: Control 5, 65535=On, 0=Off
- control: 5
  type: switch
  name: Sample Mute
  on_value: 65535
  off_value: 0
```

Field notes:

- Common: `control`, `type`, `name`
- For `type: number`: `scale`, `min`, `max`, `step`
- For `type: switch`: `on_value`, `off_value`

After changing `symetrix_controls.yaml`, restart Home Assistant to apply.

---

### 5. Bi-directional Sync and `Last TCP message`

For automatic HA state updates when you change values on Symetrix directly, Symetrix must push control updates.

**Important: enable Push in Symetrix Composer**

1. Open Symetrix Composer.
2. Go to `Tools -> Remote Control Manager`.
3. In `Control Numbers`, find controls used by HA (for example `5`, `101`).
4. Enable `Enable Push` for those controls.
5. Save and publish the configuration to DSP.

Without `Enable Push`:

- HA can still control DSP (one-way control works).
- But DSP will not push updates like `#00005=...`, so HA cannot auto-sync entity states.

For troubleshooting, temporarily enable `Last TCP message` and verify push messages are received.

**Disclaimer**  
The Symetrix logo and related trademarks are owned by Symetrix, Inc.  
This project is not affiliated with, endorsed by, or sponsored by Symetrix.

---

## [正體中文]

## Symetrix DSP Home Assistant Integration (`symetrix_ha`)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/U7U21VQTGJ)

這是一個 Home Assistant 自訂整合，用 **TCP** 指令控制 Symetrix DSP，並盡可能做到「雙向同步」：

- 從 HA 送出指令（例如 `CS 101 <value>`、`LP 1`）。
- 從 Symetrix 的 push 訊息（例如 `#00101=56173`）更新 HA 端的實體狀態。

本整合專注於 Home Assistant 與 Symetrix DSP 的 TCP 控制與狀態同步。

---

### 1. 檔案結構總覽

- `manifest.json`  
  - Home Assistant 整合宣告檔，`domain` 固定為 `symetrix_ha`。
  - 宣告使用的平台：`button`, `number`, `binary_sensor`, `sensor`, `switch`。
- `__init__.py`  
  - 實作核心的 `SymetrixClient`（常駐 TCP client）：
    - 建立與 Symetrix DSP 的 TCP 連線。
    - 啟動時送出 `GPR` / `GPU` 取得最新 preset 與 push control 列表。
    - 持續讀取以 `\r` 結尾的 TCP 資料，解析：
      - push 更新：`#00101=56173`（Control 101 值）。
      - GS 回覆：`{GS 101} 32768` 等。
    - 透過 callback 機制把控制值變化與連線狀態推送給各個 HA 實體。
  - `async_setup_entry`：
    - 從 config flow 取得 `host` / `port`。
    - 讀取 `symetrix_controls.yaml` 裡的控制清單，放到 `hass.data[DOMAIN][entry_id]["controls"]`。
    - 啟動 `SymetrixClient` 並 forward 各平台（button / number / switch / …）。
- `config_flow.py`  
  - 整合安裝用的 UI Flow：只需要輸入 `host` 與 `port`。
  - 安裝後，所有控制項目由 `symetrix_controls.yaml` 控制，不需要再在 UI 貼 YAML。
- `symetrix_controls.yaml`  
  - **你要編輯的控制清單檔案**：整合啟動時會讀取這個檔案，自動建立對應的 slider（`number`）與開關（`switch`）實體。
  - 範例內容見下方「第 4 節」。
- `button.py`  
  - 建立以下按鈕實體：
    - `Flash DSP` → `FU 4`
    - `Reboot DSP` → `R!`
    - `Reconnect` → 強制重連 (`SymetrixClient.reconnect()`)
- `switch.py`  
  - 依 `symetrix_controls.yaml` 中 `type: switch` 的條目動態建立 switch 實體。
  - 根據 push / GS 訊息自動同步開關狀態。
- `number.py`  
  - 依 `symetrix_controls.yaml` 中 `type: number` 的條目動態建立 number 實體（slider）。
  - 支援：
    - `scale: db_72_12`：把 0~65535 轉換成 -72 ~ +12 dB 顯示，反向轉換後送 `CS` 指令。
    - `scale: raw`：直接用 0~65535 作為 slider 值。
- `binary_sensor.py`  
  - `Connection` 實體：顯示是否成功連線到 Symetrix（Connectivity sensor）。
- `sensor.py`  
  - `Last TCP message`：顯示從 Symetrix 收到的最後一行原始 TCP 字串。  
  - 預設為 disabled，只有在需要除錯時建議啟用。
- `services.yaml`  
  - 定義一組服務，供自動化 / script 直接呼叫，例如：
    - `symetrix_ha.send_raw`
    - `symetrix_ha.load_preset`
    - `symetrix_ha.flash`
    - `symetrix_ha.set_value`
    - `symetrix_ha.change_value`
    - `symetrix_ha.get_latest_preset`

---

### 2. 安裝步驟

#### A. 透過 HACS 安裝（建議）

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OWNER&repository=REPO&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=symetrix_ha)

請把 HACS 連結裡的 `OWNER` / `REPO` 改成你的實際 GitHub 倉庫。

1. 在 HACS 進入 **Integrations** -> 右上選單 -> **Custom repositories**。
2. 貼上本 GitHub repository URL，類型選 **Integration**。
3. 搜尋並安裝 **Symetrix DSP TCP**。
4. 重啟 Home Assistant。
5. 到 **設定 -> 裝置與服務 -> 新增整合**，加入 **Symetrix DSP TCP**，輸入 `host` / `port`。

#### B. 手動安裝

1. 將本 repo 的 `custom_components/symetrix_ha` 複製到：
   - `/config/custom_components/symetrix_ha`
2. 重啟 Home Assistant。
3. 到 **設定 -> 裝置與服務 -> 新增整合**，加入 **Symetrix DSP TCP**，輸入 `host` / `port`。

#### 控制清單檔案

- 在 `custom_components/symetrix_ha/` 內編輯 `symetrix_controls.yaml`。
- 修改後重啟 Home Assistant，即可重新生成對應實體。

---

### 3. TCP 指令對應一覽

整合內部使用的 TCP 指令格式（每條指令末尾自動加上 `\r\n`）大致如下：

- **送原始指令**
  - 服務：`symetrix_ha.send_raw`
  - 內容：`command: "GPR"` 或其他原始指令字串
- **載入 Preset**
  - 服務：`symetrix_ha.load_preset`
  - 指令：`LP <preset>`
- **載入 Global Preset**
  - 服務：`symetrix_ha.load_global_preset`
  - 指令：`LPG <preset>`
- **Flash DSP**
  - 服務：`symetrix_ha.flash`
  - 指令：`FU <amount>`
- **Reboot DSP**
  - 服務：`symetrix_ha.reboot`
  - 指令：`R!`
- **設定控制數值**
  - 服務：`symetrix_ha.set_value`
  - 指令：`CS <control> <value>`
- **改變控制數值（增減）**
  - 服務：`symetrix_ha.change_value`
  - 指令：`CC <control> <1/0> <step>`
- **請求最新 Preset**
  - 服務：`symetrix_ha.get_latest_preset`
  - 指令：`GPR`

---

### 4. `symetrix_controls.yaml` 範例：Sample Fader / Sample Mute

`symetrix_controls.yaml` 用來描述你想要在 HA 中看到的「控制實體」列表。  
每一個條目代表一個 `number` 或 `switch`。

範例（對應你目前的預設）：

```yaml
# EXAMPLE: 輸出推桿：Control 101，對應 -72 ~ +12 dB
- control: 101
  type: number
  name: Sample Fader
  scale: db_72_12   # 以 dB 顯示，內部自動換算 0~65535
  min: -72
  max: 12
  step: 0.5

# EXAMPLE: 輸出靜音：Control 5，65535=On, 0=Off
- control: 5
  type: switch
  name: Sample Mute
  on_value: 65535
  off_value: 0
```

欄位說明：

- **共用欄位**
  - `control`：Symetrix 的 Control Number（整數）。
  - `type`：`number` 或 `switch`。
  - `name`：在 Home Assistant 中顯示的名稱。
- **`type: number` 專用欄位**
  - `scale`：
    - `db_72_12`：把 `0~65535` 映射到 `-72~+12 dB`，雙向換算。
    - `raw`：直接用 0~65535 的整數值（若省略則預設 `raw`）。
  - `min` / `max` / `step`：HA slider 的最小值、最大值與步進。
- **`type: switch` 專用欄位**
  - `on_value`：代表「開啟」時對 Symetrix 寫入的 raw 值（例如 65535）。
  - `off_value`：代表「關閉」時的 raw 值（例如 0）。

建立 / 修改 `symetrix_controls.yaml` 之後，重新啟動 HA 即可套用。

---

### 5. 雙向同步與 `Last TCP message`

當你在 Symetrix 面板上操作控制（例如移動 Fader 101、切換 Mute 5）時，  
Home Assistant 要能自動更新狀態，前提是 Symetrix 會主動推送該 control 的變化。

**重要：請在 Symetrix Composer 啟用 Push**

1. 打開 Symetrix Composer。
2. 進入 `Tools -> Remote Control Manager`。
3. 在 `Control Numbers` 清單中，找到你要給 Home Assistant 使用的 control（例如 `5`、`101`）。
4. 對這些 control 勾選或啟用 `Enable Push`。
5. 儲存並將設定發佈到 DSP。

若沒有啟用 `Enable Push`：

- HA 仍可送出指令控制 DSP（單向控制通常正常）。
- 但 DSP 不會回推像 `#00005=...` 這類訊息，HA 就無法自動同步狀態。

建議除錯時暫時啟用 `Last TCP message` 實體，確認是否有收到 push 訊息（例如 `#00101=56173`）。

**免責聲明**  
Symetrix Logo 與相關商標之權利均屬於 Symetrix, Inc.。  
本專案與 Symetrix 並無隸屬、背書或贊助關係。