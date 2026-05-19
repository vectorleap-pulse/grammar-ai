#define AppName "Grammar AI"
#define AppExeName "grammar-ai.exe"
#define AppURL "https://github.com/vectorleap-pulse/grammar-ai"

[Setup]
AppId={{F3A2B8C1-7D4E-4F8A-9B2C-1E5D8A7F3C0E}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=grammar-ai-installer-windows-x64-v{#AppVersion}
SetupIconFile=resources\icon.ico
Compression=lzma2
SolidCompression=yes
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Installer
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
; Close the running app before installing/uninstalling
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
DisableWelcomePage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "build\grammar-ai\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Interactive installs: shown as checkbox on Finish page (default checked)
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; Silent installs (auto-updates): launch app automatically after installer exits
Filename: "{app}\{#AppExeName}"; Flags: nowait; Check: WizardSilent
