#!/bin/bash
# List of repository URLs (add as many as you need)
declare -a repos=(
  "https://github.com/apache/cassandra.git"
  "https://github.com/apache/camel.git"
  "https://github.com/apache/accumulo.git"
  "https://github.com/1c-syntax/bsl-language-server.git"
)

# Create directories if they don't exist
mkdir -p external_projects logs

for repo in "${repos[@]}"
do
    # Extract project name from repo URL (e.g., 'cassandra')
    project=$(basename "$repo" .git)
    echo "Cloning $project..."
    git clone "$repo" "external_projects/$project"
    
    cd "external_projects/$project"
    
    # (Optional) Apply any instrumentation patches or modifications here.
    # For instance, you could use sed to inject your custom JUnit runner in the pom.xml
    
    echo "Building and testing $project..."
    if [ -f "pom.xml" ]; then
        # If it's a Maven project:
        mvn clean test >> ../../logs/"$project"_energy.log
    elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
        # If it's a Gradle project:
        gradle clean test >> ../../logs/"$project"_energy.log
    else
        echo "No recognized build file found for $project"
    fi
    
    cd ../..
done

