"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimeEntrySource = exports.TimeEntryKind = exports.UserRole = void 0;
var UserRole;
(function (UserRole) {
    UserRole["OWNER"] = "OWNER";
    UserRole["ADMIN"] = "ADMIN";
    UserRole["MANAGER"] = "MANAGER";
    UserRole["MEMBER"] = "MEMBER";
})(UserRole || (exports.UserRole = UserRole = {}));
var TimeEntryKind;
(function (TimeEntryKind) {
    TimeEntryKind["ACTIVE"] = "ACTIVE";
    TimeEntryKind["IDLE"] = "IDLE";
    TimeEntryKind["BREAK"] = "BREAK";
})(TimeEntryKind || (exports.TimeEntryKind = TimeEntryKind = {}));
var TimeEntrySource;
(function (TimeEntrySource) {
    TimeEntrySource["AUTO"] = "AUTO";
    TimeEntrySource["MANUAL"] = "MANUAL";
})(TimeEntrySource || (exports.TimeEntrySource = TimeEntrySource = {}));
