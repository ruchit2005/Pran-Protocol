// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title HealthcareAudit
 * @dev HIPAA-compliant audit logging smart contract
 * Records immutable audit trail for healthcare data access
 */
contract HealthcareAudit {
    
    struct AuditRecord {
        address user;           // Ethereum address of user
        string action;          // Action type (READ, WRITE, UPDATE, DELETE)
        bytes32 dataHash;       // SHA-256 hash of data
        uint256 timestamp;      // Block timestamp
        bool verified;          // Verification status
    }
    
    // Mappings
    mapping(bytes32 => AuditRecord) public records;
    mapping(address => bytes32[]) public userRecords;
    mapping(address => bool) public authorizedUsers;
    
    // Owner
    address public owner;
    
    // Events
    event RecordCreated(
        bytes32 indexed recordId,
        address indexed user,
        string action,
        bytes32 dataHash,
        uint256 timestamp
    );
    
    event RecordVerified(
        bytes32 indexed recordId,
        bool isValid
    );
    
    event UserAuthorized(address indexed user);
    event UserRevoked(address indexed user);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }
    
    modifier onlyAuthorized() {
        require(authorizedUsers[msg.sender] || msg.sender == owner, "Not authorized");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        authorizedUsers[msg.sender] = true;
    }
    
    /**
     * @dev Create a new audit record
     * @param action Type of action being logged
     * @param dataHash SHA-256 hash of the data
     * @return recordId Unique identifier for the record
     */
    function createRecord(
        string memory action,
        bytes32 dataHash
    ) public onlyAuthorized returns (bytes32) {
        
        // Generate unique record ID
        bytes32 recordId = keccak256(
            abi.encodePacked(
                msg.sender,
                action,
                dataHash,
                block.timestamp,
                block.number
            )
        );
        
        // Ensure record doesn't already exist
        require(records[recordId].timestamp == 0, "Record already exists");
        
        // Create audit record
        records[recordId] = AuditRecord({
            user: msg.sender,
            action: action,
            dataHash: dataHash,
            timestamp: block.timestamp,
            verified: true
        });
        
        // Add to user's records
        userRecords[msg.sender].push(recordId);
        
        // Emit event
        emit RecordCreated(
            recordId,
            msg.sender,
            action,
            dataHash,
            block.timestamp
        );
        
        return recordId;
    }
    
    /**
     * @dev Verify data integrity against recorded hash
     * @param recordId ID of the audit record
     * @param dataHash Hash of data to verify
     * @return bool True if hashes match
     */
    function verifyRecord(
        bytes32 recordId,
        bytes32 dataHash
    ) public view returns (bool) {
        AuditRecord memory record = records[recordId];
        
        require(record.timestamp != 0, "Record does not exist");
        
        return record.dataHash == dataHash;
    }
    
    /**
     * @dev Get audit record details
     * @param recordId ID of the audit record
     * @return Record details
     */
    function getRecord(bytes32 recordId) 
        public 
        view 
        returns (
            address user,
            string memory action,
            bytes32 dataHash,
            uint256 timestamp,
            bool verified
        ) 
    {
        AuditRecord memory record = records[recordId];
        require(record.timestamp != 0, "Record does not exist");
        
        return (
            record.user,
            record.action,
            record.dataHash,
            record.timestamp,
            record.verified
        );
    }
    
    /**
     * @dev Get all record IDs for a user
     * @param user Address of the user
     * @return Array of record IDs
     */
    function getUserRecords(address user) 
        public 
        view 
        returns (bytes32[] memory) 
    {
        return userRecords[user];
    }
    
    /**
     * @dev Authorize a new user to create records
     * @param user Address to authorize
     */
    function authorizeUser(address user) public onlyOwner {
        authorizedUsers[user] = true;
        emit UserAuthorized(user);
    }
    
    /**
     * @dev Revoke user authorization
     * @param user Address to revoke
     */
    function revokeUser(address user) public onlyOwner {
        authorizedUsers[user] = false;
        emit UserRevoked(user);
    }
    
    /**
     * @dev Check if address is authorized
     * @param user Address to check
     * @return bool Authorization status
     */
    function isAuthorized(address user) public view returns (bool) {
        return authorizedUsers[user];
    }
    
    /**
     * @dev Get total number of records for a user
     * @param user Address of the user
     * @return count Number of records
     */
    function getUserRecordCount(address user) public view returns (uint256) {
        return userRecords[user].length;
    }
}
