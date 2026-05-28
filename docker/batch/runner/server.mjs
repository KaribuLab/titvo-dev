import express from 'express'
import dockerode from 'dockerode'

console.log('Initializing batch runner server...')

const docker = new dockerode({
    socketPath: '/var/run/docker.sock'
})

console.log('Docker client initialized')

const app = express()
const port = process.env.PORT || 3001

app.use(express.json())

console.log('Express app configured')

app.post('/run-batch', async (req, res) => {
    const { containerName, environmentVariables, imageName, networkMode } = req.body
    console.log(`Running container ${containerName} with environment variables ${environmentVariables}`)
    const containers = await docker.listContainers({
        filters: {
            name: [`/${containerName}`]
        },
        all: true
    })
    const container = containers.find(container => container.Names.includes(`/${containerName}`))
    console.log(`Container ${containerName} found`)
    if (container !== null && container !== undefined) {
        console.log(`Removing container ${containerName}`)
        await docker.getContainer(container.Id).remove({
            force: true
        })
    }
    const containerEnviromentVariables = environmentVariables;
    containerEnviromentVariables.push('AWS_REGION=us-east-1')
    containerEnviromentVariables.push('AWS_DEFAULT_REGION=us-east-1')
    containerEnviromentVariables.push('AWS_ACCESS_KEY_ID=test')
    containerEnviromentVariables.push('AWS_SECRET_ACCESS_KEY=test')
    containerEnviromentVariables.push('AWS_ENDPOINT_URL=http://localstack:4566')
    const newContainer = await docker.createContainer({
        Image: imageName,
        Env: containerEnviromentVariables,
        name: containerName,
        HostConfig: {
            AutoRemove: false,
            NetworkMode: networkMode
        }
    })
    await newContainer.start()
    console.log(`Running container ${containerName} with environment variables ${environmentVariables}`)
    newContainer.logs({ follow: true, stdout: true, stderr: true }, (err, stream) => {
        if (err) {
            console.error(`Error getting logs for container ${containerName}: ${err}`)
        } else {
            stream.on('data', (data) => {
                console.log(`${data}`)
            })
        }
    })
    res.status(200).json({
        jobId: newContainer.id,
    })
})

app.post('/get-job-status', async (req, res) => {
    const { jobId } = req.body
    console.log(`Getting job status for job ${jobId}`)
    const job = await docker.getContainer(jobId)
    const status = await job.inspect()
    const dockerStatus = status.State.Status
    let batchStatus = dockerStatus.toUpperCase()

    if (dockerStatus === 'exited') {
        batchStatus = status.State.ExitCode === 0 ? 'SUCCEEDED' : 'FAILED'
    } else if (['running', 'created', 'restarting'].includes(dockerStatus)) {
        batchStatus = 'RUNNING'
    } else if (['dead', 'removing'].includes(dockerStatus)) {
        batchStatus = 'FAILED'
    }

    res.send({
        status: batchStatus
    })
})

app.listen(port, '0.0.0.0', () => {
    console.log(`✓ Batch runner server listening on port ${port}`)
    console.log(`✓ Ready to receive requests`)
})