
#define AppName "WAPT"
#define AppVersion GetFileVersion(AddBackslash(SourcePath) + "wapt-get.exe")

[Files]
Source: "C:\tranquilit\wapt\DLLs\*"; DestDir: "{app}\DLLs"; Flags: createallsubdirs recursesubdirs
Source: "C:\tranquilit\wapt\lib\*"; DestDir: "{app}\lib"; Flags: createallsubdirs recursesubdirs ; Excludes: "*.pyc,test,*.~*" 
Source: "C:\tranquilit\wapt\libs\*"; DestDir: "{app}\libs"; Flags: createallsubdirs recursesubdirs
Source: "C:\tranquilit\wapt\static\*"; DestDir: "{app}\static"; Flags: createallsubdirs recursesubdirs
Source: "C:\tranquilit\wapt\templates\*"; DestDir: "{app}\templates"; Flags: createallsubdirs recursesubdirs
Source: "C:\tranquilit\wapt\common.py"; DestDir: "{app}"; 
Source: "C:\tranquilit\wapt\winshell.py"; DestDir: "{app}"; 
Source: "C:\tranquilit\wapt\setuphelpers.py"; DestDir: "{app}"; 
Source: "C:\tranquilit\wapt\sqlite3.dll"; DestDir: "{app}"; 
Source: "C:\tranquilit\wapt\Microsoft.VC90.CRT.manifest"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\msvcm90.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\msvcp90.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\msvcr90.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\python27.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\pythoncom27.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\pythoncomloader27.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\pywintypes27.dll"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\wapt-get.ini"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\waptservice.exe"; DestDir: "{app}";  BeforeInstall: BeforeWaptServiceInstall('waptservice.exe'); AfterInstall: AfterWaptServiceInstall('waptservice.exe');
Source: "C:\tranquilit\wapt\wapt-get.py"; DestDir: "{app}"; 
Source: "C:\tranquilit\wapt\wapt-get.exe.manifest"; DestDir: "{app}";
Source: "C:\tranquilit\wapt\wapt-get.exe"; DestDir: "{app}";


[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName="C:\{#AppName}"
DefaultGroupName={#AppName}
ChangesEnvironment=True
AppPublisher=Tranquil IT Systems
UninstallDisplayName=WAPT libraries and WAPTService
OutputDir=setup
OutputBaseFilename=WaptSetup
SolidCompression=True
AppPublisherURL=http://www.tranquil.it
AppUpdatesURL=http://wapt.tranquil.it
AppContact=dev@tranquil.it
AppSupportPhone=+33 2 40 97 57 55

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}')

[INI]
Filename: {app}\wapt-get.ini; Section: global; Key: repo_url; String: {code:GetRepoURL}

[Run]


[UninstallRun]
Filename: "net"; Parameters: "stop waptservice"
Filename: "{app}\waptservice.exe"; Parameters: "--uninstall"

[Code]
#include "services.iss"
var
  RepoURLPage : TInputQueryWizardPage;
  
procedure InitializeWizard;
begin
  RepoURLPage := CreateInputQueryPage(wpWelcome,
  'Optional Parameters', 'Please specify the location of WAPT Packages (http or https URL)',
  'Leave empty if you have a DNS SRV entry for _wapt._tcp.<yourlocaldomain> giving the host and port of the Repository http server');

  // Add items (False means it's not a password edit)
  RepoURLPage.Add('Optional WAPT repository location:', False);

end;

function GetRepoURL(Param: String):String;
begin
  Result := RepoURLPage.Values[0];
end;

function InitializeSetup(): Boolean;
begin
  if ServiceExists('waptservice') then
    SimpleStopService('waptservice',True,True);
  Result := True;
end;

procedure DeinitializeSetup();
var
  ErrorCode: Integer;
begin
  if ServiceExists('waptservice') then
    SimpleStartService('waptservice',True,True);
  
end;

procedure AfterWaptServiceinstall(exe:String);
var
  ErrorCode: Integer;
begin
//  SimpleCreateService(
//   'waptservice',
//    'waptservice', 
//    ExpandConstant('"{app}\waptservice.exe" --run'),
//    SERVICE_AUTO_START,
//    '','', 
//    False, 
//    False);
  if not ShellExec('', ExpandConstant('{app}\waptservice.exe'),
     '--install', '{app}', SW_SHOW, True, ErrorCode) then
  begin
    RaiseException('Error installing waptservice:'+intToStr(ErrorCode));
  end;
   
end;

procedure BeforeWaptServiceinstall(exe:String);
begin
  if ServiceExists('waptservice') then
    SimpleDeleteService('waptservice');
end;

function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  OrigPath := '';
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;

  OrigPath := ';'+OrigPath+';';
  Result := Pos(';' + UpperCase(ExpandConstant(Param)) + ';', UpperCase(OrigPath)) = 0;
  
end;


