#!/bin/bash
# run_energy_tests.sh
# This script clones external Java projects, builds and tests them,
# and logs the output (including energy measurements if instrumented)
# to the logs folder.

# List of repository URLs
declare -a repos=(
  "https://github.com/apache/cassandra.git"
  "https://github.com/apache/camel.git"
  "https://github.com/apache/accumulo.git"
  "https://github.com/1c-syntax/bsl-language-server.git"
)

# Create necessary directories if they don't exist
mkdir -p external_projects logs

for repo in "${repos[@]}"
do
    # Extract the project name from the URL (e.g., 'cassandra')
    project=$(basename "$repo" .git)
    
    # If the project directory already exists, remove it
    if [ -d "external_projects/$project" ]; then
        echo "Directory external_projects/$project already exists. Removing it..."
        rm -rf "external_projects/$project"
    fi

    echo "Cloning $project..."
    git clone "$repo" "external_projects/$project"
    
    # Enter the project directory
    cd "external_projects/$project" || { echo "Failed to cd into $project directory."; exit 1; }
    
    echo "Building and testing $project..."

    # Check if it's a Maven project
    if [ -f "pom.xml" ]; then
        echo "$project: Detected Maven project." | tee -a ../../logs/"$project"_energy.log
        mvn clean test >> ../../logs/"$project"_energy.log 2>&1

    # Else check if it's a Gradle project
    elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
        echo "$project: Detected Gradle project." | tee -a ../../logs/"$project"_energy.log
        # Use the Gradle wrapper if available
        if [ -f "gradlew" ]; then
            echo "$project: Using Gradle wrapper." | tee -a ../../logs/"$project"_energy.log
            chmod +x gradlew
            ./gradlew clean test >> ../../logs/"$project"_energy.log 2>&1
        else
            echo "$project: Using system Gradle." | tee -a ../../logs/"$project"_energy.log
            gradle clean test >> ../../logs/"$project"_energy.log 2>&1
        fi

    # Else check if it's an Ant project
    elif [ -f "build.xml" ]; then
        echo "$project: Detected Ant project." | tee -a ../../logs/"$project"_energy.log
        ant test >> ../../logs/"$project"_energy.log 2>&1

    else
        echo "$project: No recognized build file found." | tee -a ../../logs/"$project"_energy.log
    fi
    
    # Return to the root directory of the central repository
    cd ../..
done

echo "Script completed. Check the logs directory for output."
