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
        await docker.getContainer(container.Id).remove()
    }
    const newContainer = await docker.createContainer({
        Image: imageName,
        Env: environmentVariables,
        name: containerName,
        HostConfig: {
            AutoRemove: false,
            NetworkMode: networkMode
        }
    })
    await newContainer.start()
    console.log(`Running container ${containerName} with environment variables ${environmentVariables}`)
    res.sendStatus(200)
})

app.listen(port, '0.0.0.0', () => {
    console.log(`✓ Batch runner server listening on port ${port}`)
    console.log(`✓ Ready to receive requests`)
})