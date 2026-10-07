"""Directive names used to spot typos. Unknown-but-distant names are ignored."""

UNIT_KEYS = set("""
Description Documentation Requires Requisite Wants BindsTo PartOf Upholds
Conflicts Before After OnFailure OnSuccess PropagatesReloadTo
ReloadPropagatedFrom PropagatesStopTo StopPropagatedFrom JoinsNamespaceOf
RequiresMountsFor WantsMountsFor OnSuccessJobMode OnFailureJobMode
IgnoreOnIsolate StopWhenUnneeded RefuseManualStart RefuseManualStop
AllowIsolate DefaultDependencies SurviveFinalKillSignal CollectMode
FailureAction SuccessAction FailureActionExitStatus SuccessActionExitStatus
JobTimeoutSec JobRunningTimeoutSec JobTimeoutAction JobTimeoutRebootArgument
StartLimitIntervalSec StartLimitBurst StartLimitAction RebootArgument
SourcePath StartLimitInterval
""".split())

INSTALL_KEYS = set("Alias WantedBy RequiredBy UpheldBy Also DefaultInstance".split())

SERVICE_KEYS = set("""
Type ExitType RemainAfterExit GuessMainPID PIDFile BusName ExecStart
ExecStartPre ExecStartPost ExecCondition ExecReload ExecStop ExecStopPost
RestartSec RestartSteps RestartMaxDelaySec TimeoutStartSec TimeoutStopSec
TimeoutAbortSec TimeoutSec TimeoutStartFailureMode TimeoutStopFailureMode
RuntimeMaxSec RuntimeRandomizedExtraSec WatchdogSec Restart RestartMode
SuccessExitStatus RestartPreventExitStatus RestartForceExitStatus
RootDirectoryStartOnly NonBlocking NotifyAccess Sockets FileDescriptorStoreMax
FileDescriptorStorePreserve USBFunctionDescriptors USBFunctionStrings
OOMPolicy OpenFile ReloadSignal
WorkingDirectory RootDirectory RootImage RootImageOptions RootHash
RootHashSignature RootVerity RootEphemeral MountAPIVFS ExtensionDirectories
ExtensionImages MountImages BindPaths BindReadOnlyPaths MountFlags User Group
DynamicUser SupplementaryGroups SetLoginEnvironment PAMName Nice
OOMScoreAdjust CoredumpFilter IOSchedulingClass IOSchedulingPriority
CPUSchedulingPolicy CPUSchedulingPriority CPUSchedulingResetOnFork CPUAffinity
NUMAPolicy NUMAMask UMask Environment EnvironmentFile PassEnvironment
UnsetEnvironment StandardInput StandardOutput StandardError StandardInputText
StandardInputData LogLevelMax LogExtraFields LogRateLimitIntervalSec
LogRateLimitBurst LogFilterPatterns LogNamespace SyslogIdentifier
SyslogFacility SyslogLevel SyslogLevelPrefix TTYPath TTYReset TTYVHangup
TTYVTDisallocate TTYRows TTYColumns LoadCredential LoadCredentialEncrypted
ImportCredential SetCredential SetCredentialEncrypted CapabilityBoundingSet
AmbientCapabilities NoNewPrivileges SecureBits SELinuxContext AppArmorProfile
SmackProcessLabel LimitCPU LimitFSIZE LimitDATA LimitSTACK LimitCORE LimitRSS
LimitNOFILE LimitAS LimitNPROC LimitMEMLOCK LimitLOCKS LimitSIGPENDING
LimitMSGQUEUE LimitNICE LimitRTPRIO LimitRTTIME ReadWritePaths ReadOnlyPaths
InaccessiblePaths ExecPaths NoExecPaths TemporaryFileSystem PrivateTmp
PrivateDevices PrivateNetwork NetworkNamespacePath PrivateIPC IPCNamespacePath
MemoryKSM PrivateUsers ProtectHostname ProtectClock ProtectKernelTunables
ProtectKernelModules ProtectKernelLogs ProtectControlGroups
RestrictAddressFamilies RestrictFileSystems RestrictNamespaces LockPersonality
MemoryDenyWriteExecute RestrictRealtime RestrictSUIDSGID RemoveIPC PrivatePIDs
ProtectHome ProtectSystem ProtectProc ProcSubset SystemCallFilter
SystemCallErrorNumber SystemCallArchitectures SystemCallLog Personality
RuntimeDirectory RuntimeDirectoryMode RuntimeDirectoryPreserve StateDirectory
StateDirectoryMode CacheDirectory CacheDirectoryMode LogsDirectory
LogsDirectoryMode ConfigurationDirectory ConfigurationDirectoryMode
TimeoutCleanSec DevicePolicy DeviceAllow IPAddressAllow IPAddressDeny
IPIngressFilterPath IPEgressFilterPath SocketBindAllow SocketBindDeny
RestrictNetworkInterfaces NFTSet BPFProgram DisableControllers Slice Delegate
DelegateSubgroup CPUAccounting CPUWeight StartupCPUWeight CPUQuota
CPUQuotaPeriodSec AllowedCPUs StartupAllowedCPUs AllowedMemoryNodes
StartupAllowedMemoryNodes MemoryAccounting MemoryMin MemoryLow MemoryHigh
MemoryMax MemorySwapMax MemoryZSwapMax MemoryZSwapWriteback StartupMemoryLow
StartupMemoryHigh StartupMemoryMax StartupMemorySwapMax StartupMemoryZSwapMax
ManagedOOMSwap ManagedOOMMemoryPressure ManagedOOMMemoryPressureLimit
ManagedOOMPreference MemoryPressureWatch MemoryPressureThresholdSec
IOAccounting IOWeight StartupIOWeight IODeviceWeight IOReadBandwidthMax
IOWriteBandwidthMax IOReadIOPSMax IOWriteIOPSMax IODeviceLatencyTargetSec
TasksAccounting TasksMax IPAccounting KillMode KillSignal RestartKillSignal
FinalKillSignal SendSIGHUP SendSIGKILL WatchdogSignal
MemoryLimit CPUShares StartupCPUShares BlockIOAccounting BlockIOWeight
StartupBlockIOWeight BlockIODeviceWeight BlockIOReadBandwidth
BlockIOWriteBandwidth PermissionsStartOnly SysVStartPriority
""".split())

# Directive -> (replacement, why). Used by the deprecated-directive rule.
DEPRECATED = {
    "MemoryLimit": "MemoryMax",
    "CPUShares": "CPUWeight",
    "StartupCPUShares": "StartupCPUWeight",
    "BlockIOAccounting": "IOAccounting",
    "BlockIOWeight": "IOWeight",
    "StartupBlockIOWeight": "StartupIOWeight",
    "BlockIODeviceWeight": "IODeviceWeight",
    "BlockIOReadBandwidth": "IOReadBandwidthMax",
    "BlockIOWriteBandwidth": "IOWriteBandwidthMax",
    "PermissionsStartOnly": "the '+' prefix on individual Exec lines (for example ExecStartPre=+/path)",
    "SysVStartPriority": "nothing; it is ignored by modern systemd",
}
