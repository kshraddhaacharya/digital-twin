// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PatientDigitalTwinRegistry
 * @dev Decentralized Web3 Smart Contract for Patient Digital Twin State Attestation,
 * Cryptographic Integrity Verification, and Sovereign Patient Access Control.
 */
contract PatientDigitalTwinRegistry {
    address public immutable registryDeployer;

    struct StateAttestation {
        uint256 version;
        uint256 timestamp;
        uint256 latestHR;          // scaled by 10 (e.g. 745 = 74.5 bpm)
        uint256 rollingMean;       // scaled by 10
        bytes32 stateRoot;         // SHA-256 cryptographic state hash
        string ipfsCID;            // Decentralized IPFS storage content identifier
        address attester;
        uint256 blockNumber;
    }

    struct AccessPermission {
        bool isGranted;
        uint256 expiresAt;
    }

    // Patient ID => Owner wallet address
    mapping(string => address) public patientOwners;

    // Patient ID => State Version => Attestation
    mapping(string => mapping(uint256 => StateAttestation)) public attestations;

    // Patient ID => Highest committed state version
    mapping(string => uint256) public latestVersion;

    // Patient ID => Researcher address => AccessPermission
    mapping(string => mapping(address => AccessPermission)) public permissions;

    // Events
    event PatientRegistered(string indexed patientId, address indexed owner, uint256 timestamp);
    event TwinStateAttested(
        string indexed patientId,
        uint256 indexed version,
        bytes32 stateRoot,
        string ipfsCID,
        uint256 timestamp,
        uint256 blockNumber
    );
    event AccessGranted(string indexed patientId, address indexed researcher, uint256 expiresAt);
    event AccessRevoked(string indexed patientId, address indexed researcher);

    modifier onlyPatientOwner(string memory patientId) {
        address owner = patientOwners[patientId];
        require(owner == address(0) || msg.sender == owner || msg.sender == registryDeployer, "Not authorized: Sender is not patient owner");
        _;
    }

    constructor() {
        registryDeployer = msg.sender;
    }

    /**
     * @dev Registers patient wallet address as the sovereign owner of their twin.
     */
    function registerPatient(string memory patientId, address owner) external {
        require(patientOwners[patientId] == address(0) || msg.sender == registryDeployer, "Patient already registered");
        patientOwners[patientId] = owner;
        emit PatientRegistered(patientId, owner, block.timestamp);
    }

    /**
     * @dev Commits an immutable cryptographic attestation of a Digital Twin State version to the blockchain.
     */
    function attestTwinState(
        string memory patientId,
        uint256 version,
        uint256 timestamp,
        uint256 latestHR,
        uint256 rollingMean,
        bytes32 stateRoot,
        string memory ipfsCID
    ) external onlyPatientOwner(patientId) {
        require(version > latestVersion[patientId], "Version must be strictly monotonic");

        attestations[patientId][version] = StateAttestation({
            version: version,
            timestamp: timestamp,
            latestHR: latestHR,
            rollingMean: rollingMean,
            stateRoot: stateRoot,
            ipfsCID: ipfsCID,
            attester: msg.sender,
            blockNumber: block.number
        });

        latestVersion[patientId] = version;

        emit TwinStateAttested(
            patientId,
            version,
            stateRoot,
            ipfsCID,
            timestamp,
            block.number
        );
    }

    /**
     * @dev Cryptographically verifies whether a local state hash matches the on-chain attested state.
     */
    function verifyStateAttestation(
        string memory patientId,
        uint256 version,
        bytes32 candidateHash
    ) external view returns (bool isValid, bytes32 onChainRoot, string memory ipfsCID, uint256 blockNumber) {
        StateAttestation memory att = attestations[patientId][version];
        if (att.version == 0) {
            return (false, bytes32(0), "", 0);
        }
        return (att.stateRoot == candidateHash, att.stateRoot, att.ipfsCID, att.blockNumber);
    }

    /**
     * @dev Sovereign consent: grants a clinician or researcher wallet access to read twin state.
     */
    function grantAccess(string memory patientId, address researcher, uint256 durationSeconds) external onlyPatientOwner(patientId) {
        permissions[patientId][researcher] = AccessPermission({
            isGranted: true,
            expiresAt: block.timestamp + durationSeconds
        });
        emit AccessGranted(patientId, researcher, block.timestamp + durationSeconds);
    }

    /**
     * @dev Sovereign consent: revokes researcher access.
     */
    function revokeAccess(string memory patientId, address researcher) external onlyPatientOwner(patientId) {
        permissions[patientId][researcher].isGranted = false;
        emit AccessRevoked(patientId, researcher);
    }

    /**
     * @dev Checks if a researcher or user currently has active viewing permission.
     */
    function hasAccess(string memory patientId, address user) external view returns (bool) {
        if (user == patientOwners[patientId] || user == registryDeployer) {
            return true;
        }
        AccessPermission memory p = permissions[patientId][user];
        return (p.isGranted && block.timestamp <= p.expiresAt);
    }
}
