/* Height Map Studio - Run Script entry point. No startup installation. */
(
    local studioRoot = getFilenamePath (getThisScriptFileName())
    local studioEntry = studioRoot + "launch.py"
    if (not (doesFileExist studioEntry)) do throw "Height Map Studio: launch.py is missing. Extract the complete ZIP first."
    python.ExecuteFile studioEntry
)
